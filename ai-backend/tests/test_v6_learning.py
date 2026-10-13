import os

import pytest

from app.models.base import ModelResponse
from app.orchestrator.companion import Companion


class FakeRouter:
    async def generate(self, system, messages):
        if "ONE tiny Two Pointers check" in system:
            return ModelResponse(
                "Try this: [1, 2, 3, 4, 5]. If left starts at 1 and right starts at 5, what two numbers are we looking at?",
                "fake",
                "test",
            )
        return ModelResponse("Two pointers use two positions in the array at the same time.", "fake", "test")


@pytest.mark.asyncio
async def test_two_pointer_teaching_loop_and_graph(tmp_path):
    os.environ["KNOWLEDGE_DB_PATH"] = str(tmp_path / "knowledge.db")
    c = Companion(); c.router = FakeRouter()
    a = await c.respond("wuts two pointer", "interview-demo", mode="interview")
    b = await c.respond("yea", a["conversationId"], mode="interview")
    assert b["learningState"]["waitingForAnswer"] is True
    assert any(x["name"] == "Two Pointers" for x in b["graph"]["concepts"])
    d = await c.respond("1 and 5", a["conversationId"], mode="interview")
    assert d["learningState"]["waitingForAnswer"] is True
    assert d["learningState"]["difficulty"] == "medium"
    assert any(x["type"] == "successful_application" for x in d["graph"]["evidence"])


@pytest.mark.asyncio
async def test_topic_switch_does_not_follow_old_topic(tmp_path):
    os.environ["KNOWLEDGE_DB_PATH"] = str(tmp_path / "knowledge.db")
    c = Companion(); c.router = FakeRouter()
    a = await c.respond("teach me two pointer", "switch-demo", mode="education")
    b = await c.respond("intergration", a["conversationId"], mode="education")
    assert a["topic"] == "Two Pointers"
    assert b["topic"] == "Integration"


def test_graph_does_not_create_message_nodes(tmp_path):
    os.environ["KNOWLEDGE_DB_PATH"] = str(tmp_path / "knowledge.db")
    c = Companion()
    c.graph.record("x", "self", "Learning Patterns", "I feel stuck", "uncertainty", 0.9, concept="Difficulties")
    names = [x["name"] for x in c.graph.snapshot()["concepts"]]
    assert "I Feel Stuck" not in names
    assert "Difficulties" in names


@pytest.mark.asyncio
async def test_topic_threads_pause_and_resume(tmp_path):
    os.environ["KNOWLEDGE_DB_PATH"] = str(tmp_path / "knowledge.db")
    c = Companion(); c.router = FakeRouter()
    a = await c.respond("teach me two pointers", "area-demo", mode="interview")
    b = await c.respond("intergration", a["conversationId"], mode="interview")
    c1 = await c.respond("two pointers", b["conversationId"], mode="interview")
    assert a["conversationId"] == c1["conversationId"]
    assert b["conversationId"] != a["conversationId"]
    assert c1["topic"] == "Two Pointers"
    state = c.graph.get_conversation_state(c1["conversationId"])
    assert state["topic"] == "Two Pointers"

@pytest.mark.asyncio
async def test_explicit_prerequisite_gap_is_tracked(tmp_path):
    os.environ["KNOWLEDGE_DB_PATH"] = str(tmp_path / "knowledge.db")
    c = Companion(); c.router = FakeRouter()
    a = await c.respond("teach me two pointers", "gap-demo", mode="interview")
    r = await c.respond("i dont know what a palindrome is", a["conversationId"], mode="interview")
    assert r["learningState"]["gap"] == "Palindrome definition"
    assert any(x["name"] == "Palindrome definition" for x in r["graph"]["concepts"])
    assert not any(x["name"] == "i dont know what a palindrome is" for x in r["graph"]["concepts"])

@pytest.mark.asyncio
async def test_meaningful_evidence_is_persisted_without_message_nodes(tmp_path):
    os.environ["KNOWLEDGE_DB_PATH"] = str(tmp_path / "knowledge.db")
    c = Companion(); c.router = FakeRouter()
    r = await c.respond("i think 2 sum returns the indices", "evidence-demo", mode="interview")
    snap = c.graph.snapshot()
    assert len(snap["evidence"]) >= 1
    assert any("indices" in x["message"].lower() for x in snap["evidence"])
    assert not any("i think 2 sum returns the indices" == x["name"].lower() for x in snap["concepts"])

@pytest.mark.asyncio
async def test_two_sum_is_a_distinct_resumable_topic(tmp_path):
    os.environ["KNOWLEDGE_DB_PATH"] = str(tmp_path / "knowledge.db")
    c = Companion(); c.router = FakeRouter()
    a = await c.respond("teach me two pointers", "topic-demo", mode="interview")
    b = await c.respond("two sum", a["conversationId"], mode="interview")
    c1 = await c.respond("two pointers", b["conversationId"], mode="interview")
    assert b["topic"] == "Two Sum"
    assert c1["topic"] == "Two Pointers"
    assert b["conversationId"] != a["conversationId"]
    assert c1["conversationId"] == a["conversationId"]

@pytest.mark.asyncio
async def test_graph_exposes_conversation_state(tmp_path):
    os.environ["KNOWLEDGE_DB_PATH"] = str(tmp_path / "knowledge.db")
    c = Companion(); c.router = FakeRouter()
    r = await c.respond("teach me two pointers", "state-demo", mode="interview")
    states = r["graph"].get("conversationStates", [])
    assert any(x["conversation_id"] == r["conversationId"] and x["topic"] == "Two Pointers" for x in states)

@pytest.mark.asyncio
async def test_meaningful_evidence_is_persisted_without_message_nodes(tmp_path):
    os.environ["KNOWLEDGE_DB_PATH"] = str(tmp_path / "knowledge.db")
    c = Companion(); c.router = FakeRouter()
    r = await c.respond("i think 2 sum returns the indices", "evidence-demo", mode="interview")
    snap = c.graph.snapshot()
    assert len(snap["evidence"]) >= 1
    assert any("indices" in x["message"].lower() for x in snap["evidence"])
    assert not any("i think 2 sum returns the indices" == x["name"].lower() for x in snap["concepts"])

@pytest.mark.asyncio
async def test_two_sum_is_a_distinct_resumable_topic(tmp_path):
    os.environ["KNOWLEDGE_DB_PATH"] = str(tmp_path / "knowledge.db")
    c = Companion(); c.router = FakeRouter()
    a = await c.respond("teach me two pointers", "topic-demo", mode="interview")
    b = await c.respond("two sum", a["conversationId"], mode="interview")
    c1 = await c.respond("two pointers", b["conversationId"], mode="interview")
    assert b["topic"] == "Two Sum"
    assert c1["topic"] == "Two Pointers"
    assert b["conversationId"] != a["conversationId"]
    assert c1["conversationId"] == a["conversationId"]

@pytest.mark.asyncio
async def test_graph_exposes_conversation_state(tmp_path):
    os.environ["KNOWLEDGE_DB_PATH"] = str(tmp_path / "knowledge.db")
    c = Companion(); c.router = FakeRouter()
    r = await c.respond("teach me two pointers", "state-demo", mode="interview")
    states = r["graph"].get("conversationStates", [])
    assert any(x["conversation_id"] == r["conversationId"] and x["topic"] == "Two Pointers" for x in states)
