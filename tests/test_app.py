from fastapi.testclient import TestClient

from apro.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    """Test that the /health endpoint starts up and returns the correct status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "apro",
    }
