from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class SourceNode:
    id: str
    name: str
    source_id: str
    parents: list[str] = field(default_factory=list)
    children: list[str] = field(default_factory=list)

class SourceKnowledgeGraph:
    """Source concepts/relationships. It contains no learner mastery."""
    def __init__(self):
        self.nodes: dict[str, SourceNode] = {}

    def add(self, node_id: str, name: str, source_id: str, parent_id: str | None = None):
        self.nodes.setdefault(node_id, SourceNode(node_id, name, source_id))
        if parent_id:
            self.nodes.setdefault(parent_id, SourceNode(parent_id, parent_id, source_id))
            if node_id not in self.nodes[parent_id].children:
                self.nodes[parent_id].children.append(node_id)
            if parent_id not in self.nodes[node_id].parents:
                self.nodes[node_id].parents.append(parent_id)
