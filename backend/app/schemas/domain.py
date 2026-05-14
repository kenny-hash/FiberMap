from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DeviceTypeLiteral = Literal["switch", "host", "storage"]
ProtocolLiteral = Literal["ssh", "telnet"]


class ClusterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None


class ClusterRead(ClusterCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class DeviceBase(BaseModel):
    ip: str = Field(min_length=1, max_length=64)
    type: DeviceTypeLiteral
    protocol: ProtocolLiteral | None = None
    port: int | None = Field(default=None, ge=1, le=65535)
    username: str | None = None
    password: str | None = None
    name: str | None = None


class DeviceCreate(DeviceBase):
    cluster_id: int = 1


class DeviceUpdate(BaseModel):
    ip: str | None = None
    type: DeviceTypeLiteral | None = None
    protocol: ProtocolLiteral | None = None
    port: int | None = Field(default=None, ge=1, le=65535)
    username: str | None = None
    password: str | None = None
    name: str | None = None


class DeviceRead(DeviceBase):
    id: int
    cluster_id: int
    protocol: ProtocolLiteral
    port: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DeviceImportResult(BaseModel):
    imported: int
    updated: int
    errors: list[str] = []


class DevicePortRead(BaseModel):
    id: int
    device_id: int
    name: str
    mac_address: str | None = None
    speed: str | None = None
    vlan: str | None = None
    aggregate_id: str | None = None
    link_status: str | None = None
    model_config = ConfigDict(from_attributes=True)


class TopologyNode(BaseModel):
    id: str
    label: str
    type: DeviceTypeLiteral
    ip: str


class TopologyLink(BaseModel):
    source: str
    target: str
    source_port: str | None = None
    target_port: str | None = None
    evidence: str


class TopologyRead(BaseModel):
    nodes: list[TopologyNode]
    links: list[TopologyLink]


class SnapshotRead(BaseModel):
    id: int
    cluster_id: int
    created_at: datetime
    source: str
    nodes: list[dict]
    links: list[dict]
    diff: dict
    model_config = ConfigDict(from_attributes=True)


class CollectionJobRead(BaseModel):
    id: int
    cluster_id: int
    status: str
    message: str | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
