from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4
from app import db

@dataclass
class Conversation:
    id:str; goal:Optional[str]=None; active_topic:Optional[str]=None
    messages:list[dict[str,str]]=field(default_factory=list); mode:str="education"
    learning_stage:str="explain"; difficulty:str="easy"; waiting_for_answer:bool=False
    pending_question:Optional[str]=None; pending_answer:Optional[str]=None; mastery:float=0.0
    style_level:int=0; current_gap:Optional[str]=None; status:str="active"

class ConversationStore:
    def __init__(self): self._items={}
    def _key(self,user_id,conversation_id): return f"{user_id}:{conversation_id}"
    def get_or_create(self,conversation_id=None,goal=None,mode="education"):
        uid=db.user_id()
        cid=conversation_id or str(uuid4())
        key=self._key(uid,cid)
        if key in self._items:
            c=self._items[key]
            if goal:c.goal=goal
            c.mode=mode or c.mode
            return c
        c=Conversation(id=cid,goal=goal,mode=mode)
        self._items[key]=c
        # Load durable messages for this user's thread.
        rows=db.fetchall("SELECT role,content,topic FROM messages WHERE user_id=%s AND conversation_id=%s ORDER BY created_at DESC LIMIT 12",(uid,cid))
        c.messages=[{"role":r["role"],"content":r["content"],**({"topic":r["topic"]} if r["topic"] else {})} for r in reversed(rows)]
        c._saved_count=len(c.messages)
        db.execute("""INSERT INTO conversations(id,user_id,mode) VALUES(%s,%s,%s)
                      ON CONFLICT(user_id,id) DO UPDATE SET mode=EXCLUDED.mode,updated_at=now()""",(cid,uid,mode))
        return c

    def persist_messages(self,c):
        uid=db.user_id()
        # Insert only messages that are not already represented by count; caller normally appends two.
        # We use an in-memory marker to avoid duplicate writes.
        saved=getattr(c,"_saved_count",0)
        for m in c.messages[saved:]:
            db.execute("""INSERT INTO messages(user_id,conversation_id,role,content,topic) VALUES(%s,%s,%s,%s,%s)""",
                       (uid,c.id,m.get("role","user"),m.get("content",""),m.get("topic")))
        c._saved_count=len(c.messages)
        db.execute("UPDATE conversations SET topic=%s,updated_at=now() WHERE user_id=%s AND id=%s",(c.active_topic,uid,c.id))
