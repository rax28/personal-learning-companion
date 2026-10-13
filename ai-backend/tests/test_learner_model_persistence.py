import os
import pytest

from app.knowledge.persistent_graph import PersistentKnowledgeGraph


def make_graph(tmp_path):
    path = str(tmp_path / "learner.db")
    os.environ["KNOWLEDGE_DB_PATH"] = path
    return PersistentKnowledgeGraph(path)


def test_profile_persists(tmp_path):
    g = make_graph(tmp_path)
    g.update_profile("Asha", "8", ["Algebra"], {"language": "en"})
    g2 = PersistentKnowledgeGraph(str(tmp_path / "learner.db"))
    p = g2.get_or_create_profile()
    assert p["display_name"] == "Asha"
    assert p["grade_level"] == "8"
    assert p["goals"] == ["Algebra"]
    assert p["preferences"]["language"] == "en"


def test_concepts_mastery_gaps_and_history_are_persistent(tmp_path):
    g = make_graph(tmp_path)
    g.record("c1", "education", "Fractions", "I understand numerator", "understands", .9,
             concept="Numerator", understanding_delta=.08)
    g.record("c1", "education", "Fractions", "I got it right", "successful_application", .95,
             concept="Numerator", understanding_delta=.18, attempt=True, correct=True)
    g.record("c1", "education", "Fractions", "I don't know denominators", "uncertainty", .95,
             concept="Denominator", understanding_delta=-.03)
    snap = PersistentKnowledgeGraph(str(tmp_path / "learner.db")).learner_snapshot()
    names = {x["name"] for x in snap["concepts"]}
    assert "Numerator" in names and "Denominator" in names
    assert any(x["name"] == "Denominator" for x in snap["knowledgeGaps"])
    assert len(snap["learningHistory"]) >= 3
    assert any(x["type"] == "successful_application" for x in snap["assessmentEvidence"])
    assert any(x["delta"] > 0 for x in snap["masteryUpdates"])
    assert snap["persistent"] is True


def test_relationships_are_persistent(tmp_path):
    g = make_graph(tmp_path)
    a, _ = g.ensure_concept("education", "Algebra", "Variables")
    b, _ = g.ensure_concept("education", "Algebra", "Equations")
    g.connect(a, b, "prerequisite")
    snap = PersistentKnowledgeGraph(str(tmp_path / "learner.db")).learner_snapshot()
    assert any(x["relationship"] == "prerequisite" for x in snap["relationships"])


@pytest.mark.parametrize("path_name", [
    "learning_history", "assessment_evidence", "mastery_history"
])
def test_history_api_methods_exist(tmp_path, path_name):
    g = make_graph(tmp_path)
    assert callable(getattr(g, path_name))
