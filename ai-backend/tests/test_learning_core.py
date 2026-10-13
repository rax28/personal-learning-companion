from pathlib import Path
from app.knowledge.persistent_graph import PersistentKnowledgeGraph

def test_graph_keeps_messages_as_evidence_not_nodes(tmp_path):
    db = PersistentKnowledgeGraph(str(tmp_path / "k.db"))
    db.record("c1","interview","Two Pointers","I feel stuck","uncertainty",0.9,
              concept="Moving Pointers",understanding_delta=-0.03)
    snap=db.snapshot()
    assert not any(x["name"] == "I feel stuck" for x in snap["concepts"])
    assert any(x["concept"] == "Moving Pointers" for x in snap["evidence"])
    assert any(x["name"] == "Moving Pointers" for x in snap["concepts"])

def test_conversation_state_persists(tmp_path):
    db=PersistentKnowledgeGraph(str(tmp_path/"k.db"))
    db.save_conversation_state("c1","education","Integration","practice","easy",True,"q","",2)
    state=db.get_conversation_state("c1")
    assert state["topic"]=="Integration"
    assert state["stage"]=="practice"
    assert state["waiting_for_answer"]==1
