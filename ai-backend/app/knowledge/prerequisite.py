from dataclasses import dataclass
@dataclass(frozen=True)
class Prerequisite:
    concept:str
    prerequisite:str
    weight:float=1.0
