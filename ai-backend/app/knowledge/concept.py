from dataclasses import dataclass
@dataclass(frozen=True)
class Concept:
    key:str
    name:str
    domain:str='general'
