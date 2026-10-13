class KnowledgeGraph:
    def __init__(self, prerequisites=None): self.prerequisites=prerequisites or {}
    def prerequisites_of(self, concept): return self.prerequisites.get(concept, [])
