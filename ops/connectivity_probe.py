#!/usr/bin/env python3
from urllib.request import urlopen
import json
url='https://data-api.binance.vision/api/v3/time'
try:
    with urlopen(url,timeout=10) as response:
        body=response.read(1024).decode()
        print(json.dumps({'ok':response.status==200,'status':response.status,'url':url,'body':body},indent=2))
except Exception as exc:
    print(json.dumps({'ok':False,'url':url,'error_type':type(exc).__name__,'message':str(exc)},indent=2))
    raise SystemExit(1)
