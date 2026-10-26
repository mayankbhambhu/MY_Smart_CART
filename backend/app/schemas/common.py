from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer

# Decimal in Python (exact maths), plain number in JSON (easy for the frontend).
Money = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Message(Schema):
    message: str
