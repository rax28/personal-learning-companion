from pydantic import BaseModel,Field
class Evidence(BaseModel):
    concept:str; signal:str; strength:float=Field(ge=0,le=1); confidence:float=Field(ge=0,le=1); description:str; source:str='conversation'
