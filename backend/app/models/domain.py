import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DeviceType(str, enum.Enum):
    switch = "switch"
    host = "host"
    storage = "storage"


class Protocol(str, enum.Enum):
    ssh = "ssh"
    telnet = "telnet"


class Cluster(Base):
    __tablename__ = "clusters"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    devices: Mapped[list["Device"]] = relationship(back_populates="cluster")


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint("cluster_id", "ip", name="uq_devices_cluster_ip"),
        UniqueConstraint("cluster_id", "name", name="uq_devices_cluster_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    cluster_id: Mapped[int] = mapped_column(ForeignKey("clusters.id"), index=True)
    ip: Mapped[str] = mapped_column(String(64), index=True)
    type: Mapped[DeviceType] = mapped_column(Enum(DeviceType))
    protocol: Mapped[Protocol] = mapped_column(Enum(Protocol))
    port: Mapped[int] = mapped_column(Integer)
    username: Mapped[str | None] = mapped_column(String(128), default=None)
    password: Mapped[str | None] = mapped_column(String(512), default=None)
    name: Mapped[str | None] = mapped_column(String(128), index=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    cluster: Mapped[Cluster] = relationship(back_populates="devices")
    ports: Mapped[list["DevicePort"]] = relationship(back_populates="device", cascade="all, delete-orphan")


class DevicePort(Base):
    __tablename__ = "device_ports"
    __table_args__ = (UniqueConstraint("device_id", "name", name="uq_ports_device_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    mac_address: Mapped[str | None] = mapped_column(String(64), index=True, default=None)
    speed: Mapped[str | None] = mapped_column(String(32), default=None)
    vlan: Mapped[str | None] = mapped_column(String(128), default=None)
    aggregate_id: Mapped[str | None] = mapped_column(String(128), default=None)
    link_status: Mapped[str | None] = mapped_column(String(32), default=None)

    device: Mapped[Device] = relationship(back_populates="ports")


class TopologySnapshot(Base):
    __tablename__ = "topology_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    cluster_id: Mapped[int] = mapped_column(ForeignKey("clusters.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    source: Mapped[str] = mapped_column(String(64), default="manual")
    nodes: Mapped[list[dict]] = mapped_column(JSON, default=list)
    links: Mapped[list[dict]] = mapped_column(JSON, default=list)
    diff: Mapped[dict] = mapped_column(JSON, default=dict)


class CollectionJob(Base):
    __tablename__ = "collection_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    cluster_id: Mapped[int] = mapped_column(ForeignKey("clusters.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    message: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
