from app.db.base import BaseDAO
from app.db.models import User, DeviceInfo, RegisteredDevice, SoldetDevice


class UserDAO(BaseDAO[User]):
    model = User

class RegisteredDeviceDAO(BaseDAO[RegisteredDevice]):
    model = RegisteredDevice

class DeviceInfoDAO(BaseDAO[DeviceInfo]):
    model = DeviceInfo

class SoldetDeviceDAO(BaseDAO[SoldetDevice]):
    model = SoldetDevice