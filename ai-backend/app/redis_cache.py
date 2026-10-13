from __future__ import annotations
import json, os
from redis import Redis

_client = Redis.from_url(os.getenv("REDIS_URL","redis://localhost:6379/0"), decode_responses=True)

def get(key):
    try: return _client.get(key)
    except Exception: return None

def set(key, value, ex=300):
    try: _client.setex(key, ex, value)
    except Exception: pass

def delete(key):
    try: _client.delete(key)
    except Exception: pass

def get_json(key):
    raw=get(key)
    if not raw: return None
    try: return json.loads(raw)
    except Exception: return None

def set_json(key, value, ex=300):
    set(key, json.dumps(value, ensure_ascii=False, default=str), ex)
