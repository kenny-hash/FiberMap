from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Device, TopologySnapshot
from app.schemas import TopologyLink, TopologyNode, TopologyRead


def build_topology(db: Session, cluster_id: int) -> TopologyRead:
    devices = db.scalars(select(Device).where(Device.cluster_id == cluster_id).order_by(Device.id)).all()
    nodes = [
        TopologyNode(id=str(device.id), label=device.name or device.ip, type=device.type.value, ip=device.ip)
        for device in devices
    ]
    links: list[TopologyLink] = []

    # MVP heuristic: same normalized MAC observed on two device ports is a link candidate.
    mac_to_ports: dict[str, list[tuple[Device, str]]] = {}
    for device in devices:
        for port in device.ports:
            if port.mac_address:
                normalized = port.mac_address.lower().replace("-", ":")
                mac_to_ports.setdefault(normalized, []).append((device, port.name))

    seen: set[tuple[int, int, str, str]] = set()
    for ports in mac_to_ports.values():
        if len(ports) != 2:
            continue
        (left_device, left_port), (right_device, right_port) = ports
        if left_device.id == right_device.id:
            continue
        key = tuple(sorted((left_device.id, right_device.id))) + tuple(sorted((left_port, right_port)))
        if key in seen:
            continue
        seen.add(key)
        links.append(
            TopologyLink(
                source=str(left_device.id),
                target=str(right_device.id),
                source_port=left_port,
                target_port=right_port,
                evidence="mac-table",
            )
        )

    return TopologyRead(nodes=nodes, links=links)


def diff_snapshots(previous: TopologySnapshot | None, current: TopologyRead) -> dict:
    current_nodes = {node.id for node in current.nodes}
    current_links = {(link.source, link.target, link.source_port, link.target_port) for link in current.links}
    if previous is None:
        return {
            "added_nodes": sorted(current_nodes),
            "removed_nodes": [],
            "added_links": [list(link) for link in sorted(current_links)],
            "removed_links": [],
        }

    previous_nodes = {str(node["id"]) for node in previous.nodes}
    previous_links = {
        (str(link["source"]), str(link["target"]), link.get("source_port"), link.get("target_port"))
        for link in previous.links
    }
    return {
        "added_nodes": sorted(current_nodes - previous_nodes),
        "removed_nodes": sorted(previous_nodes - current_nodes),
        "added_links": [list(link) for link in sorted(current_links - previous_links)],
        "removed_links": [list(link) for link in sorted(previous_links - current_links)],
    }


def create_snapshot(db: Session, cluster_id: int, source: str = "manual") -> TopologySnapshot:
    topology = build_topology(db, cluster_id)
    previous = db.scalars(
        select(TopologySnapshot)
        .where(TopologySnapshot.cluster_id == cluster_id)
        .order_by(TopologySnapshot.created_at.desc())
    ).first()
    snapshot = TopologySnapshot(
        cluster_id=cluster_id,
        source=source,
        nodes=[node.model_dump() for node in topology.nodes],
        links=[link.model_dump() for link in topology.links],
        diff=diff_snapshots(previous, topology),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot
