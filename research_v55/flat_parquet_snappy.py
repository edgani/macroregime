"""Small fail-closed reader for the flat Parquet subset bundled with War Room OS.

Supported: one or more row groups; flat REQUIRED/OPTIONAL scalar columns; PLAIN and
RLE_DICTIONARY/PLAIN_DICTIONARY; RLE definition levels; UNCOMPRESSED and raw SNAPPY;
BOOLEAN, INT32, INT64, FLOAT, DOUBLE and BYTE_ARRAY. Unsupported features raise.
"""
from __future__ import annotations

import json
import math
import struct
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

# TCompactProtocol wire types.
_STOP, _TRUE, _FALSE, _BYTE, _I16, _I32, _I64, _DOUBLE, _BINARY, _LIST, _SET, _MAP, _STRUCT = range(13)


class _CompactReader:
    def __init__(self, data: bytes, pos: int = 0):
        self.data = data
        self.pos = pos

    def _u8(self) -> int:
        if self.pos >= len(self.data):
            raise ValueError("truncated compact thrift")
        value = self.data[self.pos]
        self.pos += 1
        return value

    def _varint(self) -> int:
        result = shift = 0
        for _ in range(10):
            byte = self._u8()
            result |= (byte & 0x7F) << shift
            if not byte & 0x80:
                return result
            shift += 7
        raise ValueError("oversized compact thrift varint")

    def _zigzag(self) -> int:
        raw = self._varint()
        return (raw >> 1) ^ -(raw & 1)

    def value(self, wire_type: int) -> Any:
        if wire_type == _TRUE:
            return True
        if wire_type == _FALSE:
            return False
        if wire_type == _BYTE:
            value = self._u8()
            return value - 256 if value > 127 else value
        if wire_type in {_I16, _I32, _I64}:
            return self._zigzag()
        if wire_type == _DOUBLE:
            if self.pos + 8 > len(self.data):
                raise ValueError("truncated compact thrift double")
            value = struct.unpack_from("<d", self.data, self.pos)[0]
            self.pos += 8
            return value
        if wire_type == _BINARY:
            size = self._varint()
            end = self.pos + size
            if end > len(self.data):
                raise ValueError("truncated compact thrift binary")
            value = self.data[self.pos:end]
            self.pos = end
            return value
        if wire_type in {_LIST, _SET}:
            header = self._u8()
            size, element_type = header >> 4, header & 0x0F
            if size == 15:
                size = self._varint()
            return [self.value(element_type) for _ in range(size)]
        if wire_type == _MAP:
            size = self._varint()
            if size == 0:
                return []
            types = self._u8()
            key_type, value_type = types >> 4, types & 0x0F
            return [(self.value(key_type), self.value(value_type)) for _ in range(size)]
        if wire_type == _STRUCT:
            return self.struct()
        raise ValueError(f"unsupported compact thrift wire type {wire_type}")

    def struct(self) -> dict[int, Any]:
        output: dict[int, Any] = {}
        previous_field = 0
        while True:
            header = self._u8()
            if header == _STOP:
                return output
            delta, wire_type = header >> 4, header & 0x0F
            field_id = previous_field + delta if delta else self._zigzag()
            previous_field = field_id
            output[field_id] = self.value(wire_type)


def _read_uvarint(data: bytes, pos: int) -> tuple[int, int]:
    result = shift = 0
    for _ in range(10):
        if pos >= len(data):
            raise ValueError("truncated varint")
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, pos
        shift += 7
    raise ValueError("oversized varint")


def snappy_decompress(data: bytes) -> bytes:
    """Decode a raw Snappy block (the format used inside Parquet pages)."""
    expected, pos = _read_uvarint(data, 0)
    output = bytearray()
    while pos < len(data):
        tag = data[pos]
        pos += 1
        kind = tag & 0x03
        if kind == 0:  # literal
            length_code = tag >> 2
            if length_code < 60:
                length = length_code + 1
            else:
                width = length_code - 59
                if width not in {1, 2, 3, 4} or pos + width > len(data):
                    raise ValueError("invalid snappy literal length")
                length = int.from_bytes(data[pos:pos + width], "little") + 1
                pos += width
            end = pos + length
            if end > len(data):
                raise ValueError("truncated snappy literal")
            output.extend(data[pos:end])
            pos = end
            continue
        if kind == 1:
            length = 4 + ((tag >> 2) & 0x07)
            if pos >= len(data):
                raise ValueError("truncated snappy copy-1")
            offset = ((tag & 0xE0) << 3) | data[pos]
            pos += 1
        elif kind == 2:
            length = 1 + (tag >> 2)
            if pos + 2 > len(data):
                raise ValueError("truncated snappy copy-2")
            offset = int.from_bytes(data[pos:pos + 2], "little")
            pos += 2
        else:
            length = 1 + (tag >> 2)
            if pos + 4 > len(data):
                raise ValueError("truncated snappy copy-4")
            offset = int.from_bytes(data[pos:pos + 4], "little")
            pos += 4
        if offset <= 0 or offset > len(output):
            raise ValueError(f"invalid snappy offset {offset}")
        for _ in range(length):
            output.append(output[-offset])
    if len(output) != expected:
        raise ValueError(f"snappy length {len(output)} != {expected}")
    return bytes(output)


def _unpack_bits(data: bytes, bit_width: int, count: int) -> list[int]:
    if bit_width == 0:
        return [0] * count
    output: list[int] = []
    accumulator = bits = pos = 0
    mask = (1 << bit_width) - 1
    while len(output) < count:
        while bits < bit_width:
            if pos >= len(data):
                raise ValueError("truncated bit-packed values")
            accumulator |= data[pos] << bits
            bits += 8
            pos += 1
        output.append(accumulator & mask)
        accumulator >>= bit_width
        bits -= bit_width
    return output


def _decode_hybrid(data: bytes, bit_width: int, count: int) -> tuple[list[int], int]:
    """Decode Parquet RLE/bit-packed hybrid values, returning values and bytes consumed."""
    output: list[int] = []
    pos = 0
    byte_width = (bit_width + 7) // 8
    while len(output) < count:
        header, pos = _read_uvarint(data, pos)
        if header & 1 == 0:  # RLE
            run = header >> 1
            if run <= 0 or pos + byte_width > len(data):
                raise ValueError("invalid RLE run")
            value = int.from_bytes(data[pos:pos + byte_width], "little") if byte_width else 0
            pos += byte_width
            output.extend([value] * min(run, count - len(output)))
        else:  # bit-packed, count is groups of eight
            groups = header >> 1
            run_count = groups * 8
            byte_count = groups * bit_width
            end = pos + byte_count
            if groups <= 0 or end > len(data):
                raise ValueError("invalid bit-packed run")
            values = _unpack_bits(data[pos:end], bit_width, run_count)
            output.extend(values[: max(0, min(run_count, count - len(output)))])
            pos = end
    return output[:count], pos


def _plain_values(data: bytes, physical_type: int, count: int) -> tuple[list[Any], int]:
    if count == 0:
        return [], 0
    if physical_type == 0:  # BOOLEAN, bit packed LSB first
        size = (count + 7) // 8
        if len(data) < size:
            raise ValueError("truncated boolean page")
        return [bool((data[i // 8] >> (i % 8)) & 1) for i in range(count)], size
    formats = {1: ("<i", 4), 2: ("<q", 8), 4: ("<f", 4), 5: ("<d", 8)}
    if physical_type in formats:
        fmt, width = formats[physical_type]
        needed = count * width
        if len(data) < needed:
            raise ValueError("truncated numeric page")
        return [struct.unpack_from(fmt, data, i * width)[0] for i in range(count)], needed
    if physical_type == 6:  # BYTE_ARRAY
        output: list[bytes] = []
        pos = 0
        for _ in range(count):
            if pos + 4 > len(data):
                raise ValueError("truncated byte-array length")
            size = struct.unpack_from("<I", data, pos)[0]
            pos += 4
            end = pos + size
            if end > len(data):
                raise ValueError("truncated byte-array value")
            output.append(data[pos:end])
            pos = end
        return output, pos
    raise ValueError(f"unsupported Parquet physical type {physical_type}")


def _decode_page_body(body: bytes, codec: int, expected_size: int) -> bytes:
    if codec == 0:
        output = body
    elif codec == 1:
        output = snappy_decompress(body)
    else:
        raise ValueError(f"unsupported Parquet compression codec {codec}")
    if len(output) != expected_size:
        raise ValueError(f"page size {len(output)} != {expected_size}")
    return output


def _decode_column(file_data: bytes, column: dict[int, Any], schema: dict[int, Any], row_count: int) -> list[Any]:
    metadata = column.get(3)
    if not isinstance(metadata, dict):
        raise ValueError("external column metadata is unsupported")
    physical_type = int(metadata[1])
    codec = int(metadata[4])
    num_values = int(metadata[5])
    if num_values != row_count:
        raise ValueError("nested/repeated columns are unsupported")
    offsets = [int(x) for x in (metadata.get(11), metadata.get(9)) if x is not None]
    if not offsets:
        raise ValueError("missing column page offset")
    pos = min(offsets)
    end = pos + int(metadata[7])
    dictionary: list[Any] | None = None
    output: list[Any] = []
    optional = int(schema.get(3, 0)) == 1

    while pos < end and len(output) < row_count:
        header_reader = _CompactReader(file_data, pos)
        page_header = header_reader.struct()
        pos = header_reader.pos
        compressed_size = int(page_header[3])
        body_end = pos + compressed_size
        if body_end > len(file_data):
            raise ValueError("truncated Parquet page")
        body = _decode_page_body(file_data[pos:body_end], codec, int(page_header[2]))
        pos = body_end
        page_type = int(page_header[1])
        if page_type == 2:  # DICTIONARY_PAGE
            dictionary_header = page_header.get(7, {})
            count = int(dictionary_header.get(1, 0))
            encoding = int(dictionary_header.get(2, -1))
            if encoding != 0:
                raise ValueError("dictionary page must use PLAIN")
            dictionary, consumed = _plain_values(body, physical_type, count)
            if consumed != len(body):
                # Arrow can leave no padding; any non-zero remainder is unsupported.
                if any(body[consumed:]):
                    raise ValueError("unexpected dictionary page remainder")
            continue
        if page_type != 0:
            raise ValueError(f"unsupported Parquet page type {page_type}")
        data_header = page_header.get(5, {})
        page_values = int(data_header.get(1, 0))
        encoding = int(data_header.get(2, -1))
        cursor = 0
        if optional:
            if len(body) < 4:
                raise ValueError("truncated definition-level length")
            level_size = struct.unpack_from("<I", body, 0)[0]
            cursor = 4
            level_end = cursor + level_size
            if level_end > len(body):
                raise ValueError("truncated definition levels")
            definitions, consumed = _decode_hybrid(body[cursor:level_end], 1, page_values)
            if consumed > level_size:
                raise ValueError("definition levels overflow")
            cursor = level_end
        else:
            definitions = [1] * page_values
        non_null_count = sum(1 for value in definitions if value == 1)
        if encoding in {2, 8}:  # PLAIN_DICTIONARY / RLE_DICTIONARY
            if dictionary is None:
                raise ValueError("dictionary encoded page without dictionary")
            if non_null_count:
                if cursor >= len(body):
                    raise ValueError("missing dictionary bit width")
                bit_width = body[cursor]
                cursor += 1
                indices, consumed = _decode_hybrid(body[cursor:], bit_width, non_null_count)
                cursor += consumed
                try:
                    decoded = [dictionary[index] for index in indices]
                except IndexError as exc:
                    raise ValueError("dictionary index out of range") from exc
            else:
                decoded = []
        elif encoding == 0:
            decoded, consumed = _plain_values(body[cursor:], physical_type, non_null_count)
            cursor += consumed
        else:
            raise ValueError(f"unsupported Parquet encoding {encoding}")
        iterator = iter(decoded)
        output.extend(next(iterator) if level == 1 else None for level in definitions)
    if len(output) != row_count:
        raise ValueError(f"decoded {len(output)} values, expected {row_count}")
    return output


def _decode_text(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def read_flat_parquet(path: str | Path, columns: Iterable[str] | None = None, restore_pandas_index: bool = True) -> pd.DataFrame:
    path = Path(path)
    data = path.read_bytes()
    if len(data) < 12 or data[:4] != b"PAR1" or data[-4:] != b"PAR1":
        raise ValueError("not parquet")
    footer_size = struct.unpack_from("<I", data, len(data) - 8)[0]
    footer_pos = len(data) - 8 - footer_size
    if footer_pos < 4:
        raise ValueError("invalid parquet footer length")
    reader = _CompactReader(data, footer_pos)
    metadata = reader.struct()
    if reader.pos != len(data) - 8:
        raise ValueError("parquet footer length mismatch")
    schema_list = metadata.get(2, [])
    if not schema_list or int(schema_list[0].get(5, -1)) != len(schema_list) - 1:
        raise ValueError("nested or invalid schema")
    schemas = {entry[4].decode("utf-8"): entry for entry in schema_list[1:]}
    available = list(schemas)
    user_requested = available if columns is None else list(columns)
    if len(user_requested) != len(set(user_requested)):
        raise ValueError("duplicate requested columns")
    missing = [name for name in user_requested if name not in schemas]
    if missing:
        raise KeyError(f"unknown parquet columns: {missing}")

    pandas_metadata = None
    for kv in metadata.get(5, []):
        if kv.get(1) == b"pandas" and kv.get(2):
            pandas_metadata = json.loads(kv[2].decode("utf-8"))
            break
    index_columns = pandas_metadata.get("index_columns", []) if pandas_metadata else []
    index_field = index_columns[0] if len(index_columns) == 1 and isinstance(index_columns[0], str) else None
    requested = list(user_requested)
    if restore_pandas_index and index_field in schemas and index_field not in requested:
        requested.append(index_field)

    chunks: dict[str, list[Any]] = {name: [] for name in requested}
    for row_group in metadata.get(4, []):
        row_count = int(row_group.get(3, 0))
        by_name = {}
        for column in row_group.get(1, []):
            column_metadata = column.get(3, {})
            path_parts = column_metadata.get(3, [])
            if len(path_parts) != 1:
                raise ValueError("nested columns are unsupported")
            by_name[path_parts[0].decode("utf-8")] = column
        for name in requested:
            chunks[name].extend(_decode_column(data, by_name[name], schemas[name], row_count))

    frame = pd.DataFrame({name: [_decode_text(value) for value in chunks[name]] for name in requested})
    if pandas_metadata:
        type_by_field = {item.get("field_name"): item for item in pandas_metadata.get("columns", [])}
        for name in list(frame.columns):
            item = type_by_field.get(name, {})
            if item.get("pandas_type") in {"datetime", "datetimetz"}:
                frame[name] = pd.to_datetime(frame[name], unit="us", errors="raise")
        if restore_pandas_index and index_field in frame.columns:
            frame = frame.set_index(index_field)
            if index_field.startswith("__index_level_"):
                frame.index.name = None
    if columns is not None:
        visible = [name for name in user_requested if name in frame.columns]
        frame = frame[visible]
    return frame
