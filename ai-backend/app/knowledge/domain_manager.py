class DomainManager:
    def __init__(self): self.domains={}
    def register(self,name,concepts): self.domains[name]=concepts
