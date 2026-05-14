import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("FIBERMAP_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    for module in list(sys.modules):
        if module.startswith("app."):
            sys.modules.pop(module)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app.main import create_app

    return TestClient(create_app())
