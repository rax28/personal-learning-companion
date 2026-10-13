
import pytest
from app.models.base import ModelResponse
from app.orchestrator.companion import Companion

class FakeRouter:
    def __init__(self): self.calls = []
    async def generate(self, system, messages):
        self.calls.append(list(messages))
        last = messages[-1]["content"].lower()
        if "when they meet" in last:
            text = "When left and right meet or cross, you stop because there are no two separate positions left to check."
        elif "dont understand" in last or "don't understand" in last:
            text = "No worries. The pointers keep moving inward. Once they meet, there is nothing left between them to check."
        elif "where to start" in last:
            text = "Since you're preparing for interviews, I'd start with arrays and basic problem solving, then build toward hashing, two pointers, binary search, and trees."
        else:
            text = "Yeah, I get you. Let's keep going from where we were."
        return ModelResponse(text, "fake-model", "test")

@pytest.mark.asyncio
async def test_natural_context_is_preserved():
    c = Companion(); fake = FakeRouter(); c.router = fake
    a = await c.respond("i want to learn dsa but honestly i dont know where to start")
    b = await c.respond("i'm preparing for coding interviews", a["conversationId"])
    c1 = await c.respond("two pointers", b["conversationId"])
    d = await c.respond("i dont understand", c1["conversationId"])
    e = await c.respond("okay but what happens when they meet", d["conversationId"])
    assert len({a["conversationId"], b["conversationId"], c1["conversationId"], d["conversationId"], e["conversationId"]}) == 2
    assert c1["conversationId"] == d["conversationId"] == e["conversationId"]
    assert e["topic"] == "Two Pointers"
    assert "meet" in e["response"].lower()
    assert "general learning" not in e["response"].lower()
    assert len(fake.calls[-1]) >= 5

@pytest.mark.asyncio
async def test_noise_does_not_corrupt_learner_model():
    c = Companion(); c.router = FakeRouter()
    r = await c.respond("helo")
    assert r["evidence"] == []
    assert r["learnerState"]["evidence"] == []

@pytest.mark.asyncio
async def test_each_new_conversation_has_unique_id():
    c = Companion(); c.router = FakeRouter()
    a = await c.respond("teach me arrays")
    b = await c.respond("teach me recursion")
    assert a["conversationId"] != b["conversationId"]

@pytest.mark.asyncio
async def test_evidence_is_deduplicated():
    c = Companion(); c.router = FakeRouter()
    a = await c.respond("two pointers")
    await c.respond("i dont understand", a["conversationId"])
    r = await c.respond("i dont understand", a["conversationId"])
    assert len(r["learnerState"]["evidence"]) == 1
    assert r["learnerState"]["evidence"][0]["count"] == 3
