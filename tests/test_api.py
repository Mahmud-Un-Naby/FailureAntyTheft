from fastapi.testclient import TestClient

from failurealert.api import create_app


def test_health_registration_commands_and_events(tmp_path: object) -> None:
    app = create_app(
        database_path=tmp_path / "api.sqlite",  # type: ignore[operator]
        transport="inproc",
        enable_collectors=False,
    )
    with TestClient(app) as client:
        assert client.get("/api/health").json()["ready"] is True
        created = client.post(
            "/api/devices",
            json={
                "device_id": "phone-01",
                "name": "Bag phone",
                "source_url": "http://192.168.1.2:8080",
                "sensitivity": 1.5,
            },
        )
        assert created.status_code == 201
        devices = client.get("/api/devices").json()
        assert devices[0]["device_id"] == "phone-01"
        assert devices[0]["runtime"]["last_state"] == "offline"
        updated = client.patch(
            "/api/devices/phone-01",
            json={"name": "Updated bag", "sensitivity": 2.25},
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "Updated bag"
        assert updated.json()["sensitivity"] == 2.25
        assert client.patch("/api/devices/missing", json={"name": "Nope"}).status_code == 404
        assert client.post("/api/devices/phone-01/arm").status_code == 202
        assert client.post("/api/devices/missing/arm").status_code == 404
        assert client.get("/api/events").json() == []
        assert client.get("/").status_code == 200


def test_registration_rejects_public_destination(tmp_path: object) -> None:
    app = create_app(
        database_path=tmp_path / "api.sqlite",  # type: ignore[operator]
        transport="inproc",
        enable_collectors=False,
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/devices",
            json={
                "device_id": "phone-01",
                "name": "Phone",
                "source_url": "http://8.8.8.8:8080",
            },
        )
        assert response.status_code == 422


def test_websocket_receives_command_state_update(tmp_path: object) -> None:
    app = create_app(
        database_path=tmp_path / "ws.sqlite",  # type: ignore[operator]
        transport="inproc",
        enable_collectors=False,
    )
    with TestClient(app) as client:
        assert (
            client.post(
                "/api/devices",
                json={
                    "device_id": "phone-01",
                    "name": "Phone",
                    "source_url": "http://192.168.1.2:8080",
                },
            ).status_code
            == 201
        )
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"action": "subscribe_chart", "device_id": "phone-01"})
            assert client.post("/api/devices/phone-01/arm").status_code == 202
            message = websocket.receive_json()
            assert message["schema_version"] == 1
            assert message["type"] == "state"
            assert message["payload"]["device_id"] == "phone-01"
            assert message["payload"]["desired_armed"] is True
