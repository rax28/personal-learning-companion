from __future__ import annotations

import re
from typing import Any

from app.orchestrator.conversation_store import ConversationStore, Conversation
from app.orchestrator.model_router import ModelRouter
from app.learner.learner_model import LearnerModel
from app.learner.evidence_extractor import EvidenceExtractor
from app.knowledge.persistent_graph import PersistentKnowledgeGraph
from app.teaching.teaching_engine import TeachingEngine
from app.source_cache import CompressedSourceCache
from app.memory.memory_manager import MemoryManager

class Companion:
    """Gap-first tutor with resumable topic threads and a durable learner graph."""

    TOPICS = {
        "two pointers": "Two Pointers", "two pointer": "Two Pointers", "2 pointer": "Two Pointers", "2 pointers": "Two Pointers",
        "sliding window": "Sliding Window", "binary search": "Binary Search", "recursion": "Recursion", "recursive": "Recursion",
        "backtracking": "Backtracking", "greedy": "Greedy", "dynamic programming": "Dynamic Programming", "dp": "Dynamic Programming",
        "linked list": "Linked Lists", "linked lists": "Linked Lists", "linkedlist": "Linked Lists", "stack": "Stacks", "queue": "Queues",
        "binary tree": "Binary Trees", "bst": "Binary Search Trees", "binary search tree": "Binary Search Trees", "graph": "Graphs", "graphs": "Graphs",
        "hashmap": "Hash Maps", "hash map": "Hash Maps", "hash maps": "Hash Maps", "two sum": "Two Sum", "2sum": "Two Sum", "2 sum": "Two Sum", "heap": "Heaps", "priority queue": "Priority Queues", "sorting": "Sorting",
        "sort": "Sorting", "string": "Strings", "strings": "Strings", "matrix": "Matrices", "prefix sum": "Prefix Sums",
        "bit manipulation": "Bit Manipulation", "trie": "Tries", "union find": "Union Find", "disjoint set": "Union Find",
        "integration": "Integration", "integral": "Integration", "integrals": "Integration", "intergration": "Integration", "intergrate": "Integration", "integeration": "Integration",
        "derivative": "Derivatives", "derivatives": "Derivatives", "differentiation": "Differentiation", "calculus": "Calculus", "limits": "Limits", "limit": "Limits",
        "probability": "Probability", "statistics": "Statistics", "algebra": "Algebra", "geometry": "Geometry",
        "social science": "Social Science", "social studies": "Social Science", "civics": "Civics", "democracy": "Democracy", "federalism": "Federalism",
        "economics": "Economics", "history": "History", "geography": "Geography", "political science": "Civics",
        "my learning": "Learning Patterns", "how i learn": "Learning Patterns", "self understanding": "Self Understanding", "my strengths": "Strengths", "my weakness": "Difficulties",
        "interview": "Interview Prep", "behavioral": "Behavioral Interview", "behavioral interview": "Behavioral Interview",
    }

    def __init__(self):
        self.router = ModelRouter()
        self.learner = LearnerModel()
        self.evidence = EvidenceExtractor()
        self.conversations = ConversationStore()
        self.graph = PersistentKnowledgeGraph()
        self.teaching = TeachingEngine()
        self.source_cache = CompressedSourceCache()
        self.memory = MemoryManager()

    @staticmethod
    def _slug(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "general"

    def _thread_id(self, mode: str, topic: str | None) -> str:
        return f"topic:{mode}:{self._slug(topic or 'general learning')}"

    def _topic(self, text: str, current: str | None, hint: str | None = None) -> str | None:
        if hint and hint.strip():
            return hint.strip()
        low = text.lower().strip()
        for key in sorted(self.TOPICS, key=len, reverse=True):
            if re.search(rf"(?<!\w){re.escape(key)}(?!\w)", low):
                return self.TOPICS[key]
        for phrase in ("i want to learn ", "i wanna learn ", "i want to study ", "i wanna study ", "teach me ", "let's learn ", "lets learn ", "learn ", "study "):
            if low.startswith(phrase):
                rest = low[len(phrase):].strip()
                for key in sorted(self.TOPICS, key=len, reverse=True):
                    if key in rest:
                        return self.TOPICS[key]
                return rest.title() if rest else current
        return current

    @staticmethod
    def _mode_label(mode: str) -> str:
        return {"education": "Education", "self": "Self Understanding", "interview": "Interview Prep"}.get(mode, mode.title())

    @staticmethod
    def _confusion(text: str) -> bool:
        low = text.lower()
        return any(x in low for x in ["dont understand", "don't understand", "i dont get", "i don't get", "confused", "stuck", "cant get", "can't get", "idk", "i don't know", "i dont know"])

    @staticmethod
    def _understood(text: str) -> bool:
        low = text.lower().strip()
        return any(x in low for x in ["i understand", "i understood", "i got it", "got it", "understood", "makes sense", "yea", "yeah", "yep", "yes", "i get it"])

    @staticmethod
    def _move_on(text: str) -> bool:
        low = text.lower().strip()
        return any(x in low for x in ["move on", "next thing", "next topic", "something else", "different topic", "change topic", "leave this"])

    @staticmethod
    def _asks_gap(text: str) -> bool:
        low = text.lower()
        return "gap" in low and any(x in low for x in ["what", "wut", "where", "current", "find"])

    @staticmethod
    def _casual(text: str) -> bool:
        low = text.lower()
        return any(x in low for x in ["wut", "wuts", "yea", "yeah", "nah", "aight", "idk", "helo", "hahah", "lol"])

    @staticmethod
    def _gap_from_message(message: str, topic: str | None, current_gap: str | None) -> str | None:
        low = message.lower()
        if "palindrome" in low and any(x in low for x in ["don't know", "dont know", "don't understand", "dont understand", "what is", "wuts", "whats"]):
            return "Palindrome definition"
        if topic and any(x in low for x in ["don't understand", "dont understand", "stuck", "confused", "idk", "don't know", "dont know"]):
            return current_gap or f"{topic} — smallest missing idea"
        return current_gap

    def _graph_context(self, mode: str, topic: str | None) -> dict[str, Any]:
        data = self.graph.snapshot()
        concepts = data["concepts"]
        t = (topic or "").lower()
        current = [x for x in concepts if x["mode"] == mode and (not t or t in x["name"].lower() or x["name"].lower() in t or t in x["topic"].lower())]
        gaps = [x for x in concepts if x["mode"] == mode and float(x.get("understanding", 0)) < 0.55 and int(x.get("attempts", 0)) > 0]
        current.sort(key=lambda x: float(x.get("understanding", 0)))
        gaps.sort(key=lambda x: float(x.get("understanding", 0)))
        return {"current_area": current[:8], "current_mode_gaps": gaps[:6]}

    def _prompt(self, c: Conversation, learner: dict[str, Any], graph_context: dict[str, Any], instruction: str) -> str:
        history = "\n".join(
            f"{('Learner' if m['role'] == 'user' else 'Companion')}: {m['content']}"
            for m in c.messages[-8:]
        )
        return f"""
You are a personal learning companion having a real conversation with one learner.
You are not a lesson generator, lecturer, chatbot persona, or motivational coach.
Your job is to notice what the learner needs right now, respond to that, and keep the learning state moving.

AREA: {self._mode_label(c.mode)}
CURRENT TOPIC: {c.active_topic or "Unknown"}
CURRENT GAP: {c.current_gap or "Not established"}
STAGE: {c.learning_stage}
DIFFICULTY: {c.difficulty}
WAITING FOR ANSWER: {c.waiting_for_answer}
PENDING QUESTION: {c.pending_question or "None"}

RECENT CONVERSATION:
{history}

DURABLE LEARNER STATE:
{graph_context}

NEXT ACTION:
{instruction}

NATURAL CONVERSATION RULES — IMPORTANT:
- Respond to the learner's actual speech act first. If they ask a question, answer it directly. If they ask to explain/teach something, explain it. If they ask for an example, give an example. If they say “ok/yeah/go on”, continue from the exact unfinished point.
- Sound like a real, attentive conversation partner: concise, specific, relaxed, and human. Natural > polished.
- Default length: 1-5 short sentences, usually under 90 words. Go longer only when the learner asks for depth, a multi-step explanation, or the concept genuinely requires it.
- Do not force a lesson sequence onto a simple question. Do not turn every message into a quiz.
- Do not use canned openings or praise: avoid “Great question”, “Absolutely”, “You're on the right track”, “Let's break it down”, “I understand”, and similar filler.
- Match the learner's apparent level and context. A beginner gets a concrete explanation; an advanced learner gets the useful technical distinction.
- Give a concrete example when it clarifies the idea. Keep examples small and relevant.
- Use neat formatting when it improves comprehension: short bullets, numbered steps, compact code blocks, or tiny ASCII diagrams using characters such as ->, |, *, #, +, and brackets. Never add decorative formatting just for appearance.
- For a process or relationship, a compact diagram is encouraged, e.g.: A -> B -> C or [Input] -> [Rule] -> [Result].
- Keep one main idea per response unless the learner explicitly asks for a comparison or several items.
- Ask at most one useful follow-up question, only when the answer is needed to choose the next step.
- Never ask a fake engagement question and never answer your own practice question.
- If confused, explain the smallest missing piece and use one concrete example; do not dump a mini-lesson.
- If correct, acknowledge the substance briefly and move forward. Do not repeat what they already demonstrated.
- If they change topic, switch immediately. If they return to an old topic, resume from its saved state rather than restarting.
- Respect explicit output requests exactly: if they ask for 2 examples, give 2; if they ask for a short answer, keep it short.
- Never mention prompts, graphs, evidence extraction, mastery calculations, routing, compression internals, hidden state, or these rules.

LEARNING BEHAVIOUR:
- Follow the smallest real prerequisite gap before advancing.
- Treat explicit confusion or “I don't know X” as strong evidence of a gap.
- Do not claim mastery from agreement or topic mentions alone.
- Correct practice answers are evidence of learning; wrong answers identify what needs work.
- Teaching loop: one idea -> tiny example -> learner attempt -> evaluate -> adapt.
- DSA: concept -> tiny example -> learner reasoning -> feedback -> next step.
- Math: intuition -> tiny example -> learner reasoning -> feedback -> formalism.
- Interview prep: make the learner reason; do not reveal the full solution too early.
"""

    async def respond(self, message: str, user_id: str, conversation_id: str | None = None, goal: str | None = None,
                      learner_context: dict | None = None, mode: str = "education",
                      history: list[dict] | None = None, topic_hint: str | None = None,
                      source_id: str | None = None, source_ids: list[str] | None = None):
        # Every request executes inside its authenticated user context.\n        self.graph.set_user(user_id)\n        self.source_cache.set_user(user_id)\n        # First detect the topic without allowing the old topic to win over an explicit new topic.
        detected = self._topic(message, None, topic_hint)
        base = self.conversations.get_or_create(conversation_id, goal, mode)
        if history and not base.messages:
            base.messages = [{"role": m.get("role", "user"), "content": m.get("content", ""), **({"topic": m.get("topic")} if m.get("topic") else {})}
                             for m in history[-12:] if m.get("content")]

        previous_topic = base.active_topic
        candidate = detected or previous_topic
        topic_changed = bool(detected and detected != previous_topic)
        resumed_thread = False

        # A topic is its own resumable thread. Switching never overwrites the previous topic.
        if topic_changed and detected:
            target_id = self._thread_id(mode, detected)
            c = self.conversations.get_or_create(target_id, goal, mode)
            saved = self.graph.get_conversation_state(target_id)
            if saved:
                resumed_thread = True
                c.active_topic = saved.get("topic") or detected
                c.learning_stage = saved.get("stage") or "explain"
                c.difficulty = saved.get("difficulty") or "easy"
                c.waiting_for_answer = bool(saved.get("waiting_for_answer"))
                c.pending_question = saved.get("pending_question")
                c.pending_answer = saved.get("pending_answer")
                c.style_level = int(saved.get("style_level") or 0)
                c.current_gap = saved.get("current_gap")
                c.status = saved.get("status") or "active"
            else:
                c.active_topic = detected
                c.learning_stage = "explain"
                c.waiting_for_answer = False
                c.pending_question = None
                c.pending_answer = None
                c.current_gap = None
                c.status = "active"
            if history and not c.messages:
                c.messages = [{"role": m.get("role", "user"), "content": m.get("content", ""), **({"topic": m.get("topic")} if m.get("topic") else {})}
                              for m in history if m.get("content") and (not m.get("topic") or m.get("topic", "").lower() == detected.lower())][-12:]
        else:
            c = base
            if candidate:
                c.active_topic = candidate

        if self._move_on(message):
            c.status = "paused"
            c.learning_stage = "paused"
            c.waiting_for_answer = False
            c.pending_question = None
            c.pending_answer = None
            c.messages.append({"role": "user", "content": message})
            response = "Sure. We can leave this here. What do you want to work on next?"
            c.messages.append({"role": "assistant", "content": response})
            self.graph.save_conversation_state(c.id, mode, c.active_topic, c.learning_stage, c.difficulty, False, None, None, c.style_level, c.current_gap, c.status)
            return self._result(c, response, [], learner_context)

        # Resume an existing thread when explicitly returning to its topic.
        if c.status == "paused" and c.active_topic:
            c.status = "active"
            c.learning_stage = "explain" if not c.waiting_for_answer else c.learning_stage

        if self._casual(message):
            c.style_level = min(5, c.style_level + 1)

        current_gap = self._gap_from_message(message, c.active_topic, c.current_gap)
        if current_gap:
            c.current_gap = current_gap

        active_source_ids = list(dict.fromkeys([x for x in (([source_id] if source_id else []) + (source_ids or [])) if isinstance(x, str) and x]))
        source_results = []
        for sid in active_source_ids:
            for x in self.source_cache.search(sid, message, limit=4):
                source_results.append({**x, "source_id": sid})
        source_results.sort(key=lambda x: (-float(x.get("score", 0)), x.get("source_id", ""), int(x.get("index", 0))))
        source_results = source_results[:8]
        source_context = "\n\n".join(
            f"[Source {x['source_id']} | chunk {x['index']} | relevance {x['score']}]\n{x['text']}"
            for x in source_results
        )

        pending_result = None
        confusion = self._confusion(message)
        understood = self._understood(message)
        if c.waiting_for_answer and not topic_changed and message.strip():
            pending_result = self.teaching.evaluate_pending(c.active_topic or "", message, c.pending_question)
            c.pending_answer = message

        c.messages.append({"role": "user", "content": message, "topic": c.active_topic})

        evidence = self.evidence.extract(message, c.goal, {"currentRootBlock": (c.active_topic or "").lower()})
        explicit_prereq_gap = bool(current_gap and current_gap != c.active_topic and "— smallest missing idea" not in current_gap)
        if explicit_prereq_gap and confusion:
            evidence = [{"concept": current_gap, "signal": "uncertainty", "strength": 1.0, "confidence": 0.95,
                         "description": "Learner explicitly identified a missing prerequisite."}]

        # Persist every meaningful evidence event, even when it is not strong enough
        # to change mastery. This is the missing write-through step that keeps the
        # graph faithful to the actual conversation.
        if evidence and not (pending_result and pending_result[0] != "answer_attempt") and not confusion and not understood:
            items = evidence if isinstance(evidence, list) else [evidence]
            for item in items:
                self.graph.record_evidence(
                    c.id, mode, c.active_topic or "General Learning", message,
                    str(item.get("signal", "uncertainty")),
                    float(item.get("confidence", 0.5)),
                    concept=item.get("concept") or c.active_topic or "General Learning",
                )

        if pending_result and pending_result[0] != "answer_attempt":
            signal, correct, delta = pending_result
            c.learning_stage = "practice" if correct else "retry"
            c.waiting_for_answer = True
            c.difficulty = "medium" if correct and c.difficulty == "easy" else ("hard" if correct else "easy")
            if correct:
                c.pending_question = None
            evidence = [{"concept": c.current_gap or c.active_topic or "general learning", "signal": signal,
                         "strength": 1.0, "confidence": 0.95,
                         "description": "Correct practice answer." if correct else "Practice answer needs correction."}]
            self.graph.record(c.id, mode, c.active_topic or "General Learning", message,
                              "successful_application" if correct else "practice_error", 0.95,
                              concept=c.current_gap or c.active_topic or "General Learning", understanding_delta=delta,
                              attempt=True, correct=correct, parent=c.active_topic if c.current_gap else None)
        elif confusion:
            c.learning_stage = "explain"
            c.waiting_for_answer = False
            c.pending_question = None
            if c.active_topic:
                self.graph.record(c.id, mode, c.active_topic, message, "uncertainty", 0.9,
                                  concept=(c.current_gap if explicit_prereq_gap else c.active_topic), understanding_delta=-0.03,
                                  parent=c.active_topic if explicit_prereq_gap else None)
        elif understood:
            c.learning_stage = "practice"
            c.waiting_for_answer = True
            c.difficulty = "easy"
            if c.active_topic:
                self.graph.record(c.id, mode, c.active_topic, message, "understands", 0.9,
                                  concept=(c.current_gap if explicit_prereq_gap else c.active_topic), understanding_delta=0.08,
                                  parent=c.active_topic if explicit_prereq_gap else None)
        elif c.active_topic and (topic_changed or len(message.strip()) > 4):
            self.graph.record(c.id, mode, c.active_topic, message, "asked", 0.7,
                              concept=c.active_topic, understanding_delta=0.0)

        if self._asks_gap(message):
            instruction = f"Answer the learner's question about their current gap directly. Their current smallest gap is: {c.current_gap or 'not established yet'}. Do not invent another gap. If not established, say what is still unclear based on the latest evidence."
        elif pending_result and pending_result[0] == "answer_attempt":
            instruction = "The answer is not confidently scorable by deterministic rules. Do not invent a grade. Ask one short clarification or give a tiny hint."
        elif pending_result:
            _, correct, _ = pending_result
            instruction = ("The learner answered correctly. Briefly say why, then give ONE slightly harder practice question and WAIT."
                           if correct else
                           "The learner answered incorrectly. Explain the smallest missing piece, then ask the SAME small question again and WAIT.")
        elif confusion:
            instruction = f"Teach the smallest missing idea: {c.current_gap or 'identify the immediate prerequisite from the latest message'}. Use one tiny concrete example. Do not jump ahead. Do not give a new practice problem until understanding is demonstrated."
        elif understood:
            instruction = self.teaching.practice_instruction(c.active_topic or "the current concept", mode, c.difficulty)
        elif topic_changed:
            instruction = (f"Resume {c.active_topic} from the saved point. Briefly tell the learner where they left off: {c.current_gap or 'the last saved learning step'}. Then continue with exactly the next small action; do not restart from zero." if resumed_thread else
                           f"Start {c.active_topic} at the learner's level. Explain only the first small idea and a tiny example. If a prerequisite gap is obvious, teach that first.")
        else:
            instruction = "Respond naturally to the latest message while staying on the current learning state. If the learner asks to continue learning, teach only the next smallest step."

        # Only pass this topic thread's history to the model.
        # Only pass this topic thread's history to the model.
        prompt_context = self._graph_context(mode, c.active_topic)

        # Retrieve semantically relevant long-term memories for this user.
        try:
            relevant_memories = await self.memory.relevant(message, limit=3)
        except Exception as exc:
            print(f"Memory retrieval failed: {exc}")
            relevant_memories = []

        if relevant_memories:
            memory_context = "\n".join(
                f"- {item['content']}"
                for item in relevant_memories
            )
            prompt_context["RELEVANT_LONG_TERM_MEMORIES"] = memory_context

            instruction += (
                "\n\nUse RELEVANT_LONG_TERM_MEMORIES as supplementary context "
                "about this learner. Apply them only when relevant to the current "
                "question. Current instructions and the learner's latest message "
                "take priority over older memories."
            )
        if source_context:
            prompt_context["SOURCE_CACHE_EVIDENCE"] = source_context
            instruction = (instruction + "\n\nUse the retrieved source evidence below when it answers the learner's question. "
                           "Treat it as the authoritative source for source-specific facts. "
                           "If it does not contain the answer, say that the source does not establish it. "
                           "Do not invent source facts.\n\n" + source_context)

        model_response = await self.router.generate(
            system=self._prompt(c, learner_context or {}, prompt_context, instruction),
            messages=c.messages[-12:],
        )

        if c.learning_stage in {"practice", "retry"} and c.waiting_for_answer:
            c.pending_question = model_response.text

        c.messages.append({"role": "assistant", "content": model_response.text, "topic": c.active_topic})
        # Store the exchange for future semantic retrieval.
        try:
            await self.memory.store(
                message,
                kind="learner_message",
                importance=0.6,
            )
        except Exception as exc:
            print(f"Memory storage failed: {exc}")
        learner_state = self.learner.apply_evidence(evidence)
        self.graph.save_conversation_state(c.id, mode, c.active_topic, c.learning_stage, c.difficulty,
                                           c.waiting_for_answer, c.pending_question, c.pending_answer,
                                           c.style_level, c.current_gap, c.status)
        return self._result(c, model_response.text, evidence, learner_state)

    def _result(self, c: Conversation, response: str, evidence: list | dict, learner_state: dict | None):
        graph = self.graph.snapshot()
        current = {"mode": c.mode, "topic": c.active_topic, "gap": c.current_gap, "stage": c.learning_stage,
                   "difficulty": c.difficulty, "waitingForAnswer": c.waiting_for_answer, "status": c.status}
        # The SQLite graph is the durable learner state. Keep the lightweight
        # legacy learner summary for compatibility, while exposing the full
        # persistent profile/history/mastery/relationship view.
        persistent_learner = self.graph.learner_snapshot()
        return {"response": response, "conversationId": c.id, "topic": c.active_topic, "mode": c.mode,
                "evidence": evidence,
                "learnerState": {
                    **(learner_state or {}),
                    "graph": graph,
                    "current": current,
                    "profile": persistent_learner["profile"],
                    "concepts": persistent_learner["concepts"],
                    "knowledgeGaps": persistent_learner["knowledgeGaps"],
                    "learningHistory": persistent_learner["learningHistory"],
                    "assessmentEvidence": persistent_learner["assessmentEvidence"],
                    "masteryUpdates": persistent_learner["masteryUpdates"],
                    "relationships": persistent_learner["relationships"],
                    "learningGraph": persistent_learner["learningGraph"],
                    "persistent": True,
                },
                "learningState": current, "graph": graph}
