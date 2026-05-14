from io import BytesIO

import pandas as pd


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_import_csv_defaults_and_export(client):
    csv_content = "ip,type,username,password,name\n10.0.0.1,switch,admin,secret,sw-1\n10.0.0.2,host,root,secret,host-1\n"
    response = client.post(
        "/api/devices/import",
        files={"file": ("devices.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 200
    assert response.json()["imported"] == 2

    devices = client.get("/api/devices").json()
    assert devices[0]["protocol"] == "telnet"
    assert devices[0]["port"] == 23
    assert devices[1]["protocol"] == "ssh"
    assert devices[1]["port"] == 22

    exported = client.get("/api/devices/export")
    assert exported.status_code == 200
    assert "sw-1" in exported.text


def test_import_excel(client):
    frame = pd.DataFrame(
        [{"ip": "10.0.1.1", "type": "storage", "protocol": "ssh", "port": 2222, "name": "st-1"}]
    )
    stream = BytesIO()
    frame.to_excel(stream, index=False)
    stream.seek(0)

    response = client.post(
        "/api/devices/import",
        files={"file": ("devices.xlsx", stream.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 200
    assert response.json()["imported"] == 1
    assert client.get("/api/devices").json()[0]["port"] == 2222


def test_topology_snapshot_and_collection_job(client):
    for payload in [
        {"ip": "10.0.0.1", "type": "switch", "name": "switch-a"},
        {"ip": "10.0.0.2", "type": "host", "name": "host-a"},
    ]:
        assert client.post("/api/devices", json=payload).status_code == 200

    assert client.post("/api/demo/ports").status_code == 200
    topology = client.get("/api/topology").json()
    assert len(topology["nodes"]) == 2
    assert len(topology["links"]) == 1
    assert topology["links"][0]["evidence"] == "mac-table"

    snapshot = client.post("/api/snapshots").json()
    assert snapshot["diff"]["added_nodes"] == ["1", "2"]

    job = client.post("/api/collection-jobs").json()
    assert job["status"] == "completed"
