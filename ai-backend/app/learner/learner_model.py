from __future__ import annotations

class LearnerModel:
    """Lightweight response summary. Durable mastery/evidence is SQLite-backed."""
    def __init__(self):
        self.version=1
        self.knowledge={}
        self.gaps=[]
        self.misconceptions=[]
        self.evidence=[]
        self.progress=[]

    def apply(self,evidence):
        if not evidence: return self.snapshot()
        items=evidence if isinstance(evidence,list) else [evidence]
        for item in items:
            concept=item.get("concept","unknown")
            signal=item.get("signal","uncertainty")
            key=(concept,signal,item.get("description",""))
            existing=next((x for x in self.evidence if (x.get("concept"),x.get("signal"),x.get("description",""))==key),None)
            if existing:
                existing["count"]=existing.get("count",1)+1
            else:
                self.evidence.append({**dict(item),"count":1})
            if signal=="misconception":
                if not any(m["concept"]==concept and m["description"]==item.get("description","") for m in self.misconceptions):
                    self.misconceptions.append({"concept":concept,"description":item.get("description",""),
                                                "confidence":item.get("confidence",0.0),"status":"open","repairAttempts":0})
                continue
            k=self.knowledge.setdefault(concept,{"mastery":0.0,"confidence":0.0,"evidenceCount":0})
            k["evidenceCount"]+=1
            k["confidence"]=max(k["confidence"],float(item.get("confidence",0)))
            if signal in {"uncertainty","misconception","repeated_error"}:
                if not any(g["concept"]==concept for g in self.gaps):
                    self.gaps.append({"concept":concept,"confidence":k["confidence"],"source":"learning evidence"})
            elif signal=="understands":
                k["mastery"]=min(1.0,k["mastery"]+0.08*float(item.get("strength",1)))
            elif signal=="successful_application":
                k["mastery"]=min(1.0,k["mastery"]+0.18*float(item.get("strength",1)))
        self.version+=1
        return self.snapshot()

    def snapshot(self):
        return {"version":self.version,"knowledge":self.knowledge,"gaps":self.gaps,
                "misconceptions":self.misconceptions,"evidence":self.evidence,"progress":self.progress}
    def apply_evidence(self,evidence): return self.apply(evidence)
