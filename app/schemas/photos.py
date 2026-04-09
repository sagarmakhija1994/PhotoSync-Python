# app/schemas/photos.py

from pydantic import BaseModel, Field
from typing import Literal


class PhotoCheckRequest(BaseModel):
    sha256: str = Field(min_length=64, max_length=64)
    file_size: int
    media_type: Literal["photo", "video"]


class PhotoCheckResponse(BaseModel):
    exists: bool
