from pydantic import BaseModel,Field
class ChatRequest(BaseModel):
    message:str=Field(min_length=1)
    goal:dict|None=None
    learnerState:dict={}
