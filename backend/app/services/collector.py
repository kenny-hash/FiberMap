from sqlalchemy.orm import Session

from app.models import CollectionJob
from app.services.topology import create_snapshot


def enqueue_collection(db: Session, cluster_id: int) -> CollectionJob:
    """Create a collection job placeholder and complete it synchronously for the MVP.

    The API shape intentionally leaves room for a future worker + queue implementation. The MVP stores
    the job record, creates a topology snapshot from currently known inventory/port data, and marks the
    job completed so CI and local demos can exercise the full path without external devices.
    """

    job = CollectionJob(cluster_id=cluster_id, status="running", message="MVP synchronous collection")
    db.add(job)
    db.commit()
    db.refresh(job)

    create_snapshot(db, cluster_id, source="collection-job")
    job.status = "completed"
    job.message = "已基于当前资产与端口数据生成拓扑快照"
    db.commit()
    db.refresh(job)
    return job
