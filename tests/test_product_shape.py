from pathlib import Path
r=Path(__file__).resolve().parents[1]
app=(r/'app.py').read_text()
for x in ['COMMAND CENTER','GLOBAL EXPLORER','OPPORTUNITY ENGINE','PORTFOLIO','RESEARCH LAB']:
 assert x in app
for x in ['file_uploader','company_inputs.json']:
 assert x not in app
assert (r/'legacy_warroom_reference'/'app.py').exists()
assert (r/'EROS.bat').exists()
print('PRODUCT_SHAPE_PASS')
