"""User model placeholder."""

from pydantic import BaseModel


class User(BaseModel):
    id: int | None = None
    email: str
    full_name: str
