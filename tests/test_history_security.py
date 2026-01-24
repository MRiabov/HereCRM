from fastapi.testclient import TestClient
from src.main import app
from src.config import settings

client = TestClient(app)

def test_history_missing_key():
    # Request without header
    response = client.get("/history/1234567890")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing Admin Key"

def test_history_invalid_key():
    # Request with invalid header
    response = client.get("/history/1234567890", headers={"X-Admin-Key": "wrong_key"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid Admin Key"

def test_history_valid_key():
    # Request with valid header
    secret = settings.secret_key
    response = client.get("/history/1234567890", headers={"X-Admin-Key": secret})
    assert response.status_code == 200
    # We expect a list (history)
    assert isinstance(response.json(), list)
