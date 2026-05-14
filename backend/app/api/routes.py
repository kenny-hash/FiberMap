from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
import pandas as pd
from io import StringIO

from app.core.database import get_db
from app.models import Cluster, Device, DevicePort, TopologySnapshot
from app.schemas import (
    ClusterCreate,
    ClusterRead,
    CollectionJobRead,
    DeviceCreate,
    DeviceImportResult,
    DeviceRead,
    DeviceUpdate,
    SnapshotRead,
    TopologyRead,
)
from app.services.collector import enqueue_collection
from app.services.device_import import ensure_cluster, import_devices, infer_port, infer_protocol
from app.services.topology import build_topology, create_snapshot

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/clusters", response_model=ClusterRead)
def create_cluster(payload: ClusterCreate, db: Session = Depends(get_db)) -> Cluster:
    cluster = Cluster(**payload.model_dump())
    db.add(cluster)
    db.commit()
    db.refresh(cluster)
    return cluster


@router.get("/clusters", response_model=list[ClusterRead])
def list_clusters(db: Session = Depends(get_db)) -> list[Cluster]:
    return list(db.scalars(select(Cluster).order_by(Cluster.id)).all())


@router.get("/devices", response_model=list[DeviceRead])
def list_devices(cluster_id: int = 1, db: Session = Depends(get_db)) -> list[Device]:
    ensure_cluster(db, cluster_id)
    return list(db.scalars(select(Device).where(Device.cluster_id == cluster_id).order_by(Device.id)).all())


@router.post("/devices", response_model=DeviceRead)
def create_device(payload: DeviceCreate, db: Session = Depends(get_db)) -> Device:
    ensure_cluster(db, payload.cluster_id)
    data = payload.model_dump()
    protocol = infer_protocol(data["type"], data.get("protocol"))
    data["protocol"] = protocol
    data["port"] = infer_port(protocol, data.get("port"))
    device = Device(**data)
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@router.patch("/devices/{device_id}", response_model=DeviceRead)
def update_device(device_id: int, payload: DeviceUpdate, db: Session = Depends(get_db)) -> Device:
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="device not found")
    data = payload.model_dump(exclude_unset=True)
    next_type = data.get("type", device.type.value)
    next_protocol = infer_protocol(next_type, data.get("protocol", device.protocol.value))
    if "protocol" in data or "type" in data:
        data["protocol"] = next_protocol
    if data.get("port") is None and ("protocol" in data or "type" in data):
        data["port"] = infer_port(next_protocol, None)
    for key, value in data.items():
        setattr(device, key, value)
    db.commit()
    db.refresh(device)
    return device


@router.post("/devices/import", response_model=DeviceImportResult)
async def upload_inventory(
    file: UploadFile = File(...), cluster_id: int = 1, db: Session = Depends(get_db)
) -> DeviceImportResult:
    content = await file.read()
    return import_devices(db, content, file.filename or "inventory.csv", cluster_id)


@router.get("/devices/export")
def export_devices(cluster_id: int = 1, db: Session = Depends(get_db)) -> StreamingResponse:
    rows = [
        {
            "ip": device.ip,
            "type": device.type.value,
            "protocol": device.protocol.value,
            "port": device.port,
            "username": device.username,
            "password": device.password,
            "name": device.name,
        }
        for device in db.scalars(select(Device).where(Device.cluster_id == cluster_id).order_by(Device.id))
    ]
    buffer = StringIO()
    pd.DataFrame(rows).to_csv(buffer, index=False)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=fibermap-devices.csv"},
    )


@router.get("/topology", response_model=TopologyRead)
def get_topology(cluster_id: int = 1, db: Session = Depends(get_db)) -> TopologyRead:
    ensure_cluster(db, cluster_id)
    return build_topology(db, cluster_id)


@router.post("/snapshots", response_model=SnapshotRead)
def snapshot(cluster_id: int = 1, db: Session = Depends(get_db)) -> TopologySnapshot:
    ensure_cluster(db, cluster_id)
    return create_snapshot(db, cluster_id)


@router.get("/snapshots", response_model=list[SnapshotRead])
def list_snapshots(cluster_id: int = 1, db: Session = Depends(get_db)) -> list[TopologySnapshot]:
    ensure_cluster(db, cluster_id)
    return list(
        db.scalars(
            select(TopologySnapshot)
            .where(TopologySnapshot.cluster_id == cluster_id)
            .order_by(TopologySnapshot.created_at.desc())
        ).all()
    )


@router.post("/collection-jobs", response_model=CollectionJobRead)
def create_collection_job(cluster_id: int = 1, db: Session = Depends(get_db)) -> CollectionJobRead:
    ensure_cluster(db, cluster_id)
    return enqueue_collection(db, cluster_id)


@router.post("/demo/ports")
def create_demo_ports(db: Session = Depends(get_db)) -> dict[str, int]:
    """Seed deterministic port evidence for local topology demos and smoke tests."""

    devices = db.scalars(select(Device).order_by(Device.id).limit(2)).all()
    if len(devices) < 2:
        raise HTTPException(status_code=400, detail="need at least two devices")
    db.add_all(
        [
            DevicePort(device_id=devices[0].id, name="100GE1/0/1", mac_address="aa:bb:cc:00:00:01"),
            DevicePort(device_id=devices[1].id, name="eth0", mac_address="aa:bb:cc:00:00:01"),
        ]
    )
    db.commit()
    return {"created": 2}
