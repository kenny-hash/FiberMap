from fastapi.testclient import TestClient

from app.main import create_app


def main() -> None:
    client = TestClient(create_app())
    assert client.get("/api/health").json() == {"status": "ok"}
    csv_content = "ip,type,name\n192.0.2.10,switch,smoke-switch\n192.0.2.11,host,smoke-host\n"
    response = client.post(
        "/api/devices/import",
        files={"file": ("smoke.csv", csv_content, "text/csv")},
    )
    response.raise_for_status()
    assert response.json()["imported"] >= 0
    assert client.get("/api/topology").status_code == 200
    print("API smoke test passed")


if __name__ == "__main__":
    main()
