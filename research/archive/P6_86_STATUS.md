# P6.86 — Free Data Acquisition Runner

Implemented:

- SEC Financial Statement Data Sets downloader with SEC contact enforcement;
- SEC current CIK/ticker mapping downloader;
- Hugging Face parquet endpoint discovery and shard hashing;
- retry, partial-file and file-signature validation;
- immutable source receipts.

The sandbox used to create this package cannot download the large binary archives, so the real data
pull is intentionally executed by the included Windows runner. The downloader is production-like but
its market outputs remain research-grade.
