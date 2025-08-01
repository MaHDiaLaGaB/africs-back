from pydantic import BaseModel

class CountryBase(BaseModel):
    name: str
    code: str  # like "LY", "EG", "DZ"

class CountryCreate(CountryBase):
    pass

class CountryOut(CountryBase):
    id: int
    class Config:
        from_attributes = True
