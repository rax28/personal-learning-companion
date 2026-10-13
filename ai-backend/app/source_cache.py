from __future__ import annotations
import base64, hashlib, json, re, zlib, time, os
from app.source_chunking import chunk_text
from app import db, redis_cache

class CompressedSourceCache:
    """Lossless source cache: Postgres is durable; Redis accelerates reads/search."""

    @staticmethod
    def _tokens(text): return {x for x in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]{1,}", text.lower()) if len(x)>1}
    @staticmethod
    def _source_id(text, source_url=None): return hashlib.sha256(f"{source_url or ''}\n{text}".encode()).hexdigest()[:20]

    def set_user(self,user_id): return db.set_user(user_id)

    def put(self,text,source_url=None,label=None):
        chunks=[]
        for c in chunk_text(source_url or "manual-source",text):
            raw=c.text.encode(); packed=zlib.compress(raw,9)
            chunks.append({"index":c.index,"payload_b64":base64.b64encode(packed).decode(),"original_bytes":len(raw),"compressed_bytes":len(packed),"terms":sorted(self._tokens(c.text))})
        sid=self._source_id(text,source_url); uid=db.user_id()
        db.execute("""INSERT INTO source_cache(user_id,source_id,label,source_url,original_bytes,compressed_bytes,chunks)
                      VALUES(%s,%s,%s,%s,%s,%s,%s::jsonb)
                      ON CONFLICT(user_id,source_id) DO UPDATE SET label=EXCLUDED.label,source_url=EXCLUDED.source_url,original_bytes=EXCLUDED.original_bytes,compressed_bytes=EXCLUDED.compressed_bytes,chunks=EXCLUDED.chunks""",
                   (uid,sid,label or source_url or "manual source",source_url,len(text.encode()),sum(x["compressed_bytes"] for x in chunks),json.dumps(chunks)))
        redis_cache.delete(f"plc:{uid}:sources")
        return self.metadata(sid)

    def metadata(self,source_id):
        row=db.fetchone("SELECT * FROM source_cache WHERE user_id=%s AND source_id=%s",(db.user_id(),source_id))
        if not row: raise KeyError(source_id)
        return {"source_id":row["source_id"],"label":row["label"],"source_url":row["source_url"],"chunks":len(row["chunks"]),"original_bytes":row["original_bytes"],"compressed_bytes":row["compressed_bytes"],"compression_ratio":row["original_bytes"]/row["compressed_bytes"] if row["compressed_bytes"] else 1.0}

    def list_metadata(self):
        uid=db.user_id(); key=f"plc:{uid}:sources"; cached=redis_cache.get_json(key)
        if cached is not None:return cached
        rows=db.fetchall("SELECT source_id,label,source_url,original_bytes,compressed_bytes,chunks FROM source_cache WHERE user_id=%s ORDER BY created_at DESC",(uid,))
        data=[{"source_id":r["source_id"],"label":r["label"],"source_url":r["source_url"],"chunks":len(r["chunks"]),"original_bytes":r["original_bytes"],"compressed_bytes":r["compressed_bytes"],"compression_ratio":r["original_bytes"]/r["compressed_bytes"] if r["compressed_bytes"] else 1.0} for r in rows]
        redis_cache.set_json(key,data,120); return data

    def _record(self,sid):
        return db.fetchone("SELECT chunks FROM source_cache WHERE user_id=%s AND source_id=%s",(db.user_id(),sid))

    def search(self,source_id,query,limit=4):
        key=f"plc:{db.user_id()}:source:{source_id}:search:{hashlib.sha256(query.encode()).hexdigest()}:{limit}"
        cached=redis_cache.get_json(key)
        if cached is not None:return cached
        row=self._record(source_id)
        if not row:return []
        q=self._tokens(query); ranked=[]
        for item in row["chunks"]:
            terms=set(item.get("terms",[])); score=len(q&terms)
            text=zlib.decompress(base64.b64decode(item["payload_b64"])).decode()
            if query.lower().strip() and query.lower().strip() in text.lower():score+=5
            if score>0:ranked.append((score,item["index"],text))
        ranked.sort(key=lambda x:(-x[0],x[1]))
        result=[{"index":i,"score":score,"text":text} for score,i,text in ranked[:limit]]
        redis_cache.set_json(key,result,120); return result

    def get(self,source_id):
        row=self._record(source_id)
        if not row:return None
        return "\n\n".join(zlib.decompress(base64.b64decode(x["payload_b64"])).decode() for x in sorted(row["chunks"],key=lambda x:x["index"]))

    def delete(self,source_id):
        existed=db.fetchone("SELECT 1 FROM source_cache WHERE user_id=%s AND source_id=%s",(db.user_id(),source_id))
        db.execute("DELETE FROM source_cache WHERE user_id=%s AND source_id=%s",(db.user_id(),source_id))
        redis_cache.delete(f"plc:{db.user_id()}:sources")
        return bool(existed)
