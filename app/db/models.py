from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, ForeignKey, Integer, String

from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None]
    first_name: Mapped[str | None]
    last_name: Mapped[str | None]

    accepted_devices: Mapped[list["RegisteredDevice"]] = relationship(
        "RegisteredDevice",
        foreign_keys="RegisteredDevice.accepted_by_id",
        back_populates="accepted_by"
    )
    sold_devices: Mapped[list["SoldetDevice"]] = relationship(
        "SoldetDevice",
        foreign_keys="SoldetDevice.sold_by_id",
        back_populates="sold_by"
    )

class DeviceInfo(Base):
    __tablename__ = "device_info"

    jan: Mapped[str] = mapped_column(String, primary_key=True)
    device_name: Mapped[str]

    registered_devices: Mapped[list["RegisteredDevice"]] = relationship(
        "RegisteredDevice", back_populates="device_info"
    )
    sold_devices: Mapped[list["SoldetDevice"]] = relationship(
        "SoldetDevice", back_populates="device_info"
    )  


class RegisteredDevice(Base):
    __tablename__ = "registered_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    imei: Mapped[str] = mapped_column(String, nullable=False, unique=True)  # Добавлено unique=True
    jan: Mapped[str] = mapped_column(String, ForeignKey("device_info.jan"), nullable=False)
    
    accepted_by_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    
    device_info: Mapped["DeviceInfo"] = relationship(
        "DeviceInfo", back_populates="registered_devices"
    )
    accepted_by: Mapped["User"] = relationship(
        "User", foreign_keys=[accepted_by_id], back_populates="accepted_devices"
    )
    sold_device: Mapped["SoldetDevice"] = relationship(
        "SoldetDevice", back_populates="registered_device", uselist=False
    )


class SoldetDevice(Base):
    __tablename__ = "sold_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    imei: Mapped[str] = mapped_column(String, ForeignKey("registered_devices.imei"), nullable=False)
    jan: Mapped[str] = mapped_column(String, ForeignKey("device_info.jan"), nullable=False)
    sale_price: Mapped[str]
    sold_by_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)

    registered_device: Mapped["RegisteredDevice"] = relationship(
        "RegisteredDevice", back_populates="sold_device"
    )
    device_info: Mapped["DeviceInfo"] = relationship(
        "DeviceInfo", back_populates="sold_devices"
    )  
    sold_by: Mapped["User"] = relationship(
        "User", foreign_keys=[sold_by_id], back_populates="sold_devices"
    )