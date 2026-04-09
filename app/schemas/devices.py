# app/schemas/devices.py

from pydantic import BaseModel, Field


class DeviceRegisterRequest(BaseModel):
    device_uid: str = Field(min_length=8, max_length=100)
    device_name: str = Field(min_length=1, max_length=100)


class DeviceRegisterResponse(BaseModel):
    status: str
