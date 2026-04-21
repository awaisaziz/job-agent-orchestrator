"""Candidate profile schema placeholders."""

from pydantic import BaseModel


class ProfileSchema(BaseModel):
    name: str
    skills: list[str] = []
