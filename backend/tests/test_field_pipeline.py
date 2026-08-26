import sys
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app

client = TestClient(app)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "online"

def test_field_archive_api():
    res = client.get("/api/field/archive")
    assert res.status_code == 200
    data = res.json()
    assert data["dataset_version"] == "field_2026_v1"
    assert data["locked"] is True
    assert data["analytical_records"] == 18432

def test_field_quality_api():
    res = client.get("/api/field/quality")
    assert res.status_code == 200
    data = res.json()
    assert "field_2026_v1_manuscript" in data or "zone_A" in data

def test_history_api():
    res = client.get("/api/history?zone=A&parameter=air_temperature&resolution=5m&mode=FIELD")
    assert res.status_code == 200
    data = res.json()
    assert data["dataset_mode"] == "FIELD"
    assert data["total_records"] > 0
    assert data["data"][0]["source"] == "SD_ARCHIVE"
    assert data["data"][0]["dataset_version"] == "field_2026_v1"

def test_history_v2_api():
    res = client.get("/api/history?zone=A&parameter=air_temperature&resolution=5m&mode=FIELD&dataset_version=field_2026_v2_september")
    assert res.status_code == 200
    data = res.json()
    assert data["total_records"] > 0
    assert data["data"][0]["dataset_version"] == "field_2026_v2_september"

def test_comparison_api():
    res = client.get("/api/comparison/summary")
    assert res.status_code == 200
    data = res.json()
    assert "microclimate_metrics" in data
    assert data["dataset_version"] == "field_2026_v1"

def test_validation_api():
    res = client.get("/api/validation/field")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "LOCKED"
    assert len(data["performance"]) == 3

def test_csv_export_api():
    res = client.get("/api/export/csv?zone=A&parameter=soil_moisture&mode=FIELD")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    content = res.text
    assert "timestamp,zone,mode,parameter,value,quality,source,dataset_version" in content
    assert "SD_ARCHIVE,field_2026_v1" in content
