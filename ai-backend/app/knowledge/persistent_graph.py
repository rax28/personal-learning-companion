from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any
from app import db, redis_cache

class PersistentKnowledgeGraph:
    """PostgreSQL-backed, user-scoped learner knowledge graph."""

    def set_user(self, user_id: str):
        return db.set_user(user_id)

    @staticmethod
    def _now(): return datetime.now(timezone.utc)
    def _cache_key(self): return f"plc:{db.user_id()}:learner-graph"
    def _invalidate(self): redis_cache.delete(self._cache_key())

    def ensure_conversation(self, conversation_id: str, mode="education", topic=None):
        uid=db.user_id()
        db.execute("""INSERT INTO conversations(id,user_id,mode,topic)
                      VALUES(%s,%s,%s,%s)
                      ON CONFLICT(user_id,id) DO UPDATE SET mode=EXCLUDED.mode, topic=COALESCE(EXCLUDED.topic,conversations.topic), updated_at=now()""",
                   (conversation_id,uid,mode,topic))

    def ensure_concept(self, mode, topic, concept=None, parent=None):
        uid=db.user_id()
        topic=(topic or "General Learning").strip()
        concept=(concept or topic).strip()
        category={"education":"Education","self":"Self Understanding","interview":"Interview Prep"}.get(mode,mode.title())
        db.execute("""INSERT INTO topics(user_id,name,category,mode) VALUES(%s,%s,%s,%s)
                      ON CONFLICT(user_id,name,mode) DO NOTHING""",(uid,topic,category,mode))
        t=db.fetchone("SELECT id FROM topics WHERE user_id=%s AND name=%s AND mode=%s",(uid,topic,mode))
        db.execute("""INSERT INTO concepts(user_id,topic_id,name,parent_id) VALUES(%s,%s,%s,NULL)
                      ON CONFLICT(user_id,topic_id,name) DO NOTHING""",(uid,t["id"],topic))
        root=db.fetchone("SELECT id FROM concepts WHERE user_id=%s AND topic_id=%s AND name=%s",(uid,t["id"],topic))
        parent_id=root["id"]
        if parent and parent.strip()!=topic:
            db.execute("""INSERT INTO concepts(user_id,topic_id,name,parent_id) VALUES(%s,%s,%s,%s)
                          ON CONFLICT(user_id,topic_id,name) DO NOTHING""",(uid,t["id"],parent.strip(),root["id"]))
            pr=db.fetchone("SELECT id FROM concepts WHERE user_id=%s AND topic_id=%s AND name=%s",(uid,t["id"],parent.strip()))
            parent_id=pr["id"]
        db.execute("""INSERT INTO concepts(user_id,topic_id,name,parent_id) VALUES(%s,%s,%s,%s)
                      ON CONFLICT(user_id,topic_id,name) DO NOTHING""",(uid,t["id"],concept,parent_id))
        row=db.fetchone("SELECT id FROM concepts WHERE user_id=%s AND topic_id=%s AND name=%s",(uid,t["id"],concept))
        if parent_id != row["id"]:
            db.execute("""INSERT INTO connections(user_id,from_concept_id,to_concept_id,relationship)
                          VALUES(%s,%s,%s,'contains') ON CONFLICT DO NOTHING""",(uid,parent_id,row["id"]))
        return int(row["id"]),int(t["id"])

    def record_evidence(self, conversation_id, mode, topic, message, evidence_type, confidence, concept=None):
        self.ensure_conversation(conversation_id,mode,topic)
        concept_name=(concept or topic).strip() or topic
        if concept_name.lower()==topic.strip().lower(): concept_name=f"{topic} — Basics"
        cid,_=self.ensure_concept(mode,topic,concept_name,topic if concept_name!=topic else None)
        db.execute("""INSERT INTO learning_evidence(user_id,conversation_id,concept_id,message,type,confidence)
                      VALUES(%s,%s,%s,%s,%s,%s)""",(db.user_id(),conversation_id,cid,message,evidence_type,max(0,min(1,confidence))))
        self._invalidate(); return self.get_concept(cid)

    def record(self, conversation_id, mode, topic, message, evidence_type, confidence,
               concept=None, understanding_delta=0.0, attempt=False, correct=False, parent=None):
        self.ensure_conversation(conversation_id,mode,topic)
        concept_name=(concept or topic).strip()
        if concept_name.lower()==topic.strip().lower():
            concept_name=f"{topic} — Basics"; parent=topic
        cid,_=self.ensure_concept(mode,topic,concept_name,parent)
        uid=db.user_id()
        db.execute("""INSERT INTO learning_evidence(user_id,conversation_id,concept_id,message,type,confidence)
                      VALUES(%s,%s,%s,%s,%s,%s)""",(uid,conversation_id,cid,message,evidence_type,max(0,min(1,confidence))))
        old=db.fetchone("SELECT * FROM mastery WHERE user_id=%s AND concept_id=%s",(uid,cid))
        current=float(old["understanding"]) if old else 0.0
        attempts=int(old["attempts"]) if old else 0
        correct_count=int(old["correct"]) if old else 0
        new=max(0,min(1,current+understanding_delta))
        attempts += int(attempt); correct_count += int(correct)
        db.execute("""INSERT INTO mastery(user_id,concept_id,understanding,attempts,correct,last_seen)
                      VALUES(%s,%s,%s,%s,%s,now())
                      ON CONFLICT(user_id,concept_id) DO UPDATE SET understanding=EXCLUDED.understanding,attempts=EXCLUDED.attempts,correct=EXCLUDED.correct,last_seen=EXCLUDED.last_seen""",
                   (uid,cid,new,attempts,correct_count))
        if understanding_delta!=0 or attempt:
            db.execute("""INSERT INTO mastery_history(user_id,concept_id,conversation_id,previous_mastery,new_mastery,delta,signal)
                          VALUES(%s,%s,%s,%s,%s,%s,%s)""",(uid,cid,conversation_id,current,new,new-current,evidence_type))
        self._invalidate(); return self.get_concept(cid)

    def get_conversation_state(self, conversation_id):
        return db.fetchone("SELECT * FROM conversation_state WHERE user_id=%s AND conversation_id=%s",(db.user_id(),conversation_id))

    def save_conversation_state(self, conversation_id, mode, topic, stage, difficulty, waiting_for_answer,
                                pending_question, pending_answer, style_level, current_gap=None, status="active"):
        db.execute("""INSERT INTO conversation_state(user_id,conversation_id,mode,topic,stage,difficulty,waiting_for_answer,pending_question,pending_answer,style_level,current_gap,status)
                      VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                      ON CONFLICT(user_id,conversation_id) DO UPDATE SET mode=EXCLUDED.mode,topic=EXCLUDED.topic,stage=EXCLUDED.stage,difficulty=EXCLUDED.difficulty,
                      waiting_for_answer=EXCLUDED.waiting_for_answer,pending_question=EXCLUDED.pending_question,pending_answer=EXCLUDED.pending_answer,
                      style_level=EXCLUDED.style_level,current_gap=EXCLUDED.current_gap,status=EXCLUDED.status,updated_at=now()""",
                   (db.user_id(),conversation_id,mode,topic,stage,difficulty,waiting_for_answer,pending_question,pending_answer,style_level,current_gap,status))
        self._invalidate()

    def connect(self,from_id,to_id,relationship):
        if from_id==to_id:return
        db.execute("""INSERT INTO connections(user_id,from_concept_id,to_concept_id,relationship)
                      VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING""",(db.user_id(),from_id,to_id,relationship))
        self._invalidate()

    def get_concept(self,concept_id):
        return db.fetchone("""SELECT c.id,c.name,c.parent_id,t.id topic_id,t.name topic,t.category,t.mode,
                      COALESCE(m.understanding,0) understanding,COALESCE(m.attempts,0) attempts,COALESCE(m.correct,0) correct,m.last_seen
                      FROM concepts c JOIN topics t ON t.id=c.topic_id AND t.user_id=c.user_id
                      LEFT JOIN mastery m ON m.concept_id=c.id AND m.user_id=c.user_id
                      WHERE c.user_id=%s AND c.id=%s""",(db.user_id(),concept_id))

    def snapshot(self):
        cached=redis_cache.get_json(self._cache_key())
        if cached is not None: return cached
        uid=db.user_id()
        rows=db.fetchall("""SELECT c.id,c.name,c.parent_id,t.name topic,t.category,t.mode,
                    COALESCE(m.understanding,0) understanding,COALESCE(m.attempts,0) attempts,COALESCE(m.correct,0) correct,m.last_seen
                    FROM concepts c JOIN topics t ON t.id=c.topic_id AND t.user_id=c.user_id
                    LEFT JOIN mastery m ON m.concept_id=c.id AND m.user_id=c.user_id
                    WHERE c.user_id=%s ORDER BY t.mode,t.name,c.parent_id,c.name""",(uid,))
        edges=db.fetchall("""SELECT f.id from_id,f.name from_name,t.id to_id,t.name to_name,x.relationship
                    FROM connections x JOIN concepts f ON f.id=x.from_concept_id AND f.user_id=x.user_id
                    JOIN concepts t ON t.id=x.to_concept_id AND t.user_id=x.user_id WHERE x.user_id=%s""",(uid,))
        evidence=db.fetchall("""SELECT e.id,e.conversation_id,e.message,e.type,e.confidence,e.created_at,c.id concept_id,c.name concept,t.mode,t.name topic
                    FROM learning_evidence e JOIN concepts c ON c.id=e.concept_id AND c.user_id=e.user_id JOIN topics t ON t.id=c.topic_id AND t.user_id=c.user_id
                    WHERE e.user_id=%s ORDER BY e.id DESC LIMIT 100""",(uid,))
        states=db.fetchall("""SELECT conversation_id,mode,topic,stage,difficulty,waiting_for_answer,pending_question,current_gap,status,updated_at
                    FROM conversation_state WHERE user_id=%s ORDER BY updated_at DESC""",(uid,))
        concepts=[dict(x) for x in rows]
        for root in [x for x in concepts if x["parent_id"] is None]:
            kids=[x for x in concepts if x["parent_id"]==root["id"]]
            if kids:
                root["understanding"]=sum(float(x["understanding"]) for x in kids)/len(kids)
                root["attempts"]=sum(int(x["attempts"]) for x in kids); root["correct"]=sum(int(x["correct"]) for x in kids)
        data={"concepts":concepts,"connections":[dict(x) for x in edges],"evidence":[dict(x) for x in evidence],"conversationStates":[dict(x) for x in states]}; redis_cache.set_json(self._cache_key(),data,30); return data

    def get_or_create_profile(self):
        uid=db.user_id()
        row=db.fetchone("SELECT * FROM learner_profile WHERE user_id=%s",(uid,))
        if not row:
            db.execute("""INSERT INTO learner_profile(user_id,display_name) VALUES(%s,%s) ON CONFLICT DO NOTHING""",(uid,"Learner"))
            row=db.fetchone("SELECT * FROM learner_profile WHERE user_id=%s",(uid,))
        data=dict(row); data["goals"]=data["goals"] if isinstance(data["goals"],list) else json.loads(data["goals"]); data["preferences"]=data["preferences"] if isinstance(data["preferences"],dict) else json.loads(data["preferences"]); return data

    def update_profile(self,display_name=None,grade_level=None,goals=None,preferences=None):
        cur=self.get_or_create_profile()
        vals=(display_name if display_name is not None else cur["display_name"],
              grade_level if grade_level is not None else cur["grade_level"],
              goals if goals is not None else cur["goals"], preferences if preferences is not None else cur["preferences"])
        db.execute("""UPDATE learner_profile SET display_name=%s,grade_level=%s,goals=%s::jsonb,preferences=%s::jsonb,updated_at=now() WHERE user_id=%s""",
                   (vals[0],vals[1],json.dumps(vals[2]),json.dumps(vals[3]),db.user_id()))
        self._invalidate(); return self.get_or_create_profile()

    def learner_gaps(self,limit=10):
        rows=db.fetchall("""SELECT c.id,c.name,t.name topic,t.mode,COALESCE(m.understanding,0) understanding,COALESCE(m.attempts,0) attempts,COALESCE(m.correct,0) correct
                    FROM concepts c JOIN topics t ON t.id=c.topic_id AND t.user_id=c.user_id LEFT JOIN mastery m ON m.concept_id=c.id AND m.user_id=c.user_id
                    WHERE c.user_id=%s AND (COALESCE(m.understanding,0)<0.55 OR COALESCE(m.attempts,0)>COALESCE(m.correct,0))
                    ORDER BY understanding ASC,attempts DESC LIMIT %s""",(db.user_id(),limit))
        return [dict(x) for x in rows]

    def learning_history(self,limit=100):
        rows=db.fetchall("""SELECT e.id,e.conversation_id,e.message,e.type,e.confidence,e.created_at,c.name concept,t.name topic,t.mode
                    FROM learning_evidence e JOIN concepts c ON c.id=e.concept_id AND c.user_id=e.user_id JOIN topics t ON t.id=c.topic_id AND t.user_id=c.user_id
                    WHERE e.user_id=%s ORDER BY e.id DESC LIMIT %s""",(db.user_id(),max(1,min(int(limit),500))))
        return [dict(x) for x in rows]

    def assessment_evidence(self,limit=100):
        rows=db.fetchall("""SELECT e.id,e.conversation_id,e.message,e.type,e.confidence,e.created_at,c.name concept,t.name topic,t.mode
                    FROM learning_evidence e JOIN concepts c ON c.id=e.concept_id AND c.user_id=e.user_id JOIN topics t ON t.id=c.topic_id AND t.user_id=c.user_id
                    WHERE e.user_id=%s AND e.type = ANY(%s) ORDER BY e.id DESC LIMIT %s""",(db.user_id(),["successful_application","practice_error","answer_attempt"],max(1,min(int(limit),500))))
        return [dict(x) for x in rows]

    def mastery_history(self,limit=100):
        rows=db.fetchall("""SELECT h.id,h.conversation_id,h.previous_mastery,h.new_mastery,h.delta,h.signal,h.created_at,c.name concept,t.name topic,t.mode
                    FROM mastery_history h JOIN concepts c ON c.id=h.concept_id AND c.user_id=h.user_id JOIN topics t ON t.id=c.topic_id AND t.user_id=c.user_id
                    WHERE h.user_id=%s ORDER BY h.id DESC LIMIT %s""",(db.user_id(),max(1,min(int(limit),500))))
        return [dict(x) for x in rows]

    def learner_snapshot(self):
        data=self.snapshot()
        gaps=[x for x in data["concepts"] if x["parent_id"] is not None and (float(x["understanding"])<0.55 or int(x["attempts"])>int(x["correct"]))]
        return {"profile":self.get_or_create_profile(),"concepts":data["concepts"],"knowledgeGaps":gaps,"learningHistory":self.learning_history(),"assessmentEvidence":self.assessment_evidence(),"masteryUpdates":self.mastery_history(),"relationships":data["connections"],"learningGraph":{"concepts":data["concepts"],"connections":data["connections"]},"persistent":True}

    def by_mode(self,mode):
        data=self.snapshot(); data["concepts"]=[x for x in data["concepts"] if x["mode"]==mode]; ids={x["id"] for x in data["concepts"]}
        data["connections"]=[x for x in data["connections"] if x["from_id"] in ids and x["to_id"] in ids]; data["evidence"]=[x for x in data["evidence"] if x["mode"]==mode]; return data
