from __future__ import annotations
import ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FORBIDDEN=('gcfis','engines','warroom.')
violations=[]
for path in (ROOT/'src/warroom_v3').rglob('*.py'):
    tree=ast.parse(path.read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            for alias in node.names:
                if alias.name.startswith(FORBIDDEN): violations.append(f'{path}:{alias.name}')
        elif isinstance(node,ast.ImportFrom) and node.module:
            if node.module.startswith(FORBIDDEN): violations.append(f'{path}:{node.module}')
if violations:
    raise SystemExit('legacy import boundary violated:\n'+'\n'.join(violations))
print('PASS: import boundaries')
