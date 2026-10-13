#!/usr/bin/env bash
set -euo pipefail

AI_BASE="${AI_BASE:-http://localhost:8000}"
GATEWAY_BASE="${GATEWAY_BASE:-http://localhost:4000}"

python - <<'PY'
import json, os, sys, urllib.request

AI=os.environ.get('AI_BASE','http://localhost:8000')
GW=os.environ.get('GATEWAY_BASE','http://localhost:4000')

def get(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return r.status, r.read().decode()

def post(url, payload):
    data=json.dumps(payload).encode()
    req=urllib.request.Request(url, data=data, headers={'Content-Type':'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.status, r.read().decode()

for name,url in [
    ('AI health', AI+'/health'),
    ('Gateway health', GW+'/health'),
    ('Gateway graph', GW+'/learning/graph'),
    ('Gateway gaps', GW+'/learning/gaps'),
    ('Gateway compression default', GW+'/compression/source-default'),
]:
    status,body=get(url)
    assert status == 200, (name,status,body[:300])
    print('PASS', name)

status,body=post(GW+'/compression/compress', {
    'text':'Understanding is compression. A learner improves by building better internal representations.',
    'model':'llama3.2',
})
assert status == 200, (status,body[:500])
packed=json.loads(body)
status,body=post(GW+'/compression/decompress', {'payload_b64':packed['payload_b64']})
assert status == 200, (status,body[:500])
assert json.loads(body)['text']=='Understanding is compression. A learner improves by building better internal representations.'
print('PASS compression round-trip')
print('ALL LIVE SMOKE TESTS PASS')
PY
