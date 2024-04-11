import pytest
from fastapi.testclient import TestClient
from ai_api_server.app import app

client = TestClient(app)

def test_add():
    assert 1 + 2 == 3

def test_status():
    response = client.get("/api/status")
    print("res:",response.json())
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, World!"}

