from pydantic import BaseModel

class SUser(BaseModel):
    id: int | None = None
    username: str | None
    first_name: str | None
    last_name: str | None

class SDeviceInfo(BaseModel):
    jan: str | None  = None
    device_name: str | None = None


class SRegisteredDevice(BaseModel):
    imei: str | None = None
    jan: str | None = None
    accepted_by_id:int | None = None

class SSoldetDevice(BaseModel):
    imei: str | None
    jan: str | None
    sold_by_id: int | None
    sale_price: str | None
