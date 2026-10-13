from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass
class Evidence:
    concept: str
    signal: str
    strength: float
    confidence: float
    description: str


class EvidenceExtractor:
    KEYWORDS = {
        "two pointers": ["two pointer", "two pointers", "2 pointer", "left pointer", "right pointer"],
        "recursion": ["recursion", "recursive", "call stack"],
        "binary search": ["binary search", "middle element"],
        "integration": ["integration", "integral", "intergration", "intergrate", "integeration"],
        "derivative": ["derivative", "slope"],
        "chain rule": ["chain rule"],
        "functions": ["function", "input", "output"],
        "civics": ["civics", "democracy", "federalism"],
        "graphs": ["graph", "graphs"],
    }

    def extract(self, text, goal=None, state=None):
        low = text.strip().lower()
        state = state or {}
        if len(low) < 3 or low in {"ok", "okay", "k", "hmm", "huh", "yo", "hey", "helo", "hello", "dude"}:
            return []

        found = next((c for c, ks in self.KEYWORDS.items() if any(k in low for k in ks)), None)
        if not found:
            active = state.get("currentRootBlock") if isinstance(state, dict) else None
            found = active if active and active != "general learning" else self._goal_concept(goal)
        if not found:
            return []

        misconception = any(x in low for x in ["simultaneously", "all at once", "must always be the answer", "always move both"])
        confusion = any(x in low for x in ["dont understand", "don't understand", "i dont get", "i don't get", "stuck", "cant get", "can't get", "confused", "idk"])
        understands = any(x in low for x in ["because", "therefore", "works by", "i understand", "i understood", "i got it", "got it", "understood", "makes sense", "yea", "yeah", "yep", "yes"])
        signal = "misconception" if misconception else ("uncertainty" if confusion else ("understands" if understands else "uncertainty"))
        description = (
            "User explicitly described a misconception." if misconception else
            "User needs guidance or shows uncertainty." if confusion else
            "User demonstrated understanding." if understands else
            "User needs guidance or shows uncertainty."
        )
        return asdict(Evidence(found, signal, 0.82 if found != "general learning" else 0.55,
                               0.9 if found != "general learning" else 0.65, description))

    @staticmethod
    def _goal_concept(goal):
        title = goal if isinstance(goal, str) else (goal or {}).get("title", "") if isinstance(goal, dict) else ""
        low = title.lower()
        return next((c for c, terms in EvidenceExtractor.KEYWORDS.items() if any(t in low for t in terms)), None)
