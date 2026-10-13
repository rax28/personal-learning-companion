from __future__ import annotations

import re


class TeachingEngine:
    """Deterministic teaching-state transitions around the LLM."""

    def classify_topic(self, topic: str | None, mode: str) -> str:
        return (topic or "General Learning").strip()

    def needs_practice(self, stage: str, understood: bool) -> bool:
        return understood and stage in {"explain", "check"}

    def evaluate_pending(self, topic: str, answer: str, question: str | None) -> tuple[str, bool, float]:
        """Return (signal, correct, mastery_delta).

        Only high-confidence tiny exercises are scored deterministically.
        Other answers are left for the LLM to judge.
        """
        low = answer.lower().strip()
        if topic.lower() in {"two pointers", "two pointer"} and question:
            if "1" in low and "5" in low:
                return "successful_application", True, 0.18
            if any(x in low for x in ["2 and 4", "2,4", "4 and 2", "2 4"]):
                return "partially_understands", False, -0.03
        if topic.lower() == "integration" and question:
            # Simple multiplication check used by the introductory integration exercise.
            nums = [int(x) for x in re.findall(r"\b\d+\b", low)]
            if nums and nums[-1] == 12:
                return "successful_application", True, 0.18
        return "answer_attempt", False, 0.0

    def practice_instruction(self, topic: str, mode: str, difficulty: str) -> str:
        if topic.lower() in {"two pointers", "two pointer"}:
            return "Give ONE tiny Two Pointers check: [1, 2, 3, 4, 5], left starts at 1 and right starts at 5. Ask what two numbers the pointers are looking at. WAIT for the learner. Do not give the answer."
        if topic.lower() == "integration":
            return "Give ONE very simple pre-calculus integration intuition check: 3 groups of 4 apples, ask for the total. Explain that this is only the intuition of adding pieces. WAIT for the learner. Do not give the answer."
        return f"Give ONE small {topic} practice question at {difficulty} difficulty. WAIT for the learner's answer and do not reveal the solution."
