from io import BytesIO
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Cluster, Device
from app.schemas import DeviceImportResult

REQUIRED_COLUMNS = {"ip", "type"}
VALID_TYPES = {"switch", "host", "storage"}
VALID_PROTOCOLS = {"ssh", "telnet"}


def infer_protocol(device_type: str, protocol: str | None) -> str:
    if protocol:
        return protocol.lower()
    return "telnet" if device_type == "switch" else "ssh"


def infer_port(protocol: str, port: Any | None) -> int:
    if port is not None and str(port).strip() and str(port).lower() != "nan":
        return int(port)
    return 23 if protocol == "telnet" else 22


def normalize_row(row: dict[str, Any], line_no: int) -> tuple[dict[str, Any] | None, str | None]:
    normalized = {str(k).strip().lower(): v for k, v in row.items()}
    missing = REQUIRED_COLUMNS - set(normalized)
    if missing:
        return None, f"第 {line_no} 行缺少字段: {', '.join(sorted(missing))}"

    ip = str(normalized.get("ip", "")).strip()
    device_type = str(normalized.get("type", "")).strip().lower()
    if not ip:
        return None, f"第 {line_no} 行 IP 不能为空"
    if device_type not in VALID_TYPES:
        return None, f"第 {line_no} 行 type 必须是 switch/host/storage"

    protocol_raw = normalized.get("protocol")
    protocol = infer_protocol(
        device_type,
        None if pd.isna(protocol_raw) or not str(protocol_raw).strip() else str(protocol_raw).strip(),
    )
    if protocol not in VALID_PROTOCOLS:
        return None, f"第 {line_no} 行 protocol 必须是 ssh 或 telnet"

    try:
        port = infer_port(protocol, normalized.get("port"))
    except (TypeError, ValueError):
        return None, f"第 {line_no} 行 port 必须是整数"

    def optional_text(key: str) -> str | None:
        value = normalized.get(key)
        if value is None or pd.isna(value) or not str(value).strip():
            return None
        return str(value).strip()

    return {
        "ip": ip,
        "type": device_type,
        "protocol": protocol,
        "port": port,
        "username": optional_text("username"),
        "password": optional_text("password"),
        "name": optional_text("name") or optional_text("rfid"),
    }, None


def read_inventory(content: bytes, filename: str) -> pd.DataFrame:
    lowered = filename.lower()
    if lowered.endswith(".csv"):
        return pd.read_csv(BytesIO(content))
    if lowered.endswith((".xlsx", ".xls")):
        return pd.read_excel(BytesIO(content))
    raise ValueError("仅支持 CSV / Excel 文件")


def ensure_cluster(db: Session, cluster_id: int, name: str = "default") -> Cluster:
    cluster = db.get(Cluster, cluster_id)
    if cluster:
        return cluster
    cluster = Cluster(id=cluster_id, name=name)
    db.add(cluster)
    db.commit()
    db.refresh(cluster)
    return cluster


def import_devices(db: Session, content: bytes, filename: str, cluster_id: int = 1) -> DeviceImportResult:
    ensure_cluster(db, cluster_id)
    frame = read_inventory(content, filename)
    imported = 0
    updated = 0
    errors: list[str] = []

    for index, row in frame.iterrows():
        payload, error = normalize_row(row.to_dict(), int(index) + 2)
        if error:
            errors.append(error)
            continue
        assert payload is not None
        existing = db.scalar(
            select(Device).where(Device.cluster_id == cluster_id, Device.ip == payload["ip"])
        )
        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
            updated += 1
        else:
            db.add(Device(cluster_id=cluster_id, **payload))
            imported += 1

    db.commit()
    return DeviceImportResult(imported=imported, updated=updated, errors=errors)
