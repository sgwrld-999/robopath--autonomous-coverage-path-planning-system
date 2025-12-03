import pytest
from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    # Since we serve index.html, we expect text/html
    assert "text/html" in response.headers["content-type"]

def test_create_trajectory():
    payload = {
        "job_name": "Test Job",
        "wall": {"width": 5.0, "height": 5.0},
        "obstacles": [
            {"x": 1.0, "y": 1.0, "width": 0.5, "height": 0.5}
        ],
        "planner_params": {
            "tool_width": 0.5,
            "overlap": 0.1,
            "safe_margin": 0.1,
            "orientation": "auto"
        }
    }
    response = client.post("/api/trajectories/", json=payload)
    if response.status_code != 201:
        print(response.json())
    assert response.status_code == 201
    data = response.json()
    assert data["job_name"] == "Test Job"
    assert "waypoints" in data
    assert len(data["waypoints"]) > 0
    assert data["meta"]["coverage_fraction"] > 0

def test_get_trajectory():
    # First create one
    payload = {
        "job_name": "Fetch Me",
        "wall": {"width": 3.0, "height": 3.0},
        "obstacles": [],
        "planner_params": {
            "tool_width": 0.5,
            "overlap": 0.1,
            "safe_margin": 0.1,
            "orientation": "vertical"
        }
    }
    create_res = client.post("/api/trajectories/", json=payload)
    assert create_res.status_code == 201
    traj_id = create_res.json()["id"]

    # Now fetch it
    response = client.get(f"/api/trajectories/{traj_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == traj_id
    assert data["job_name"] == "Fetch Me"

def test_list_trajectories():
    response = client.get("/api/trajectories/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
