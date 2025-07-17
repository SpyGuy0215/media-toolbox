import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)

def test_base_route():
    response = client.get('/')
    print("Response from base route:", response.json())
    assert response.status_code == 200