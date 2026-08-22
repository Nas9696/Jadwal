from fastapi.testclient import TestClient

from conftest import OTHER_TENANT, TEST_TENANT

def test_tenant_header_is_required(client: TestClient) -> None:
    assert client.get("/api/v1/schools").status_code == 400

def test_schools_are_isolated_by_tenant(client: TestClient) -> None:
    first = client.get("/api/v1/schools", headers={"X-Tenant-ID": TEST_TENANT})
    other = client.get("/api/v1/schools", headers={"X-Tenant-ID": OTHER_TENANT})
    assert [school["name_ar"] for school in first.json()] == ["مدرسة النور"]
    assert [school["name_ar"] for school in other.json()] == ["مدرسة أخرى"]
    assert first.json()[0]["tenant_id"] != other.json()[0]["tenant_id"]

def test_cross_tenant_dashboard_is_not_visible(client: TestClient) -> None:
    school = client.get("/api/v1/schools", headers={"X-Tenant-ID": TEST_TENANT}).json()[0]
    response = client.get(f"/api/v1/dashboard/{school['id']}", headers={"X-Tenant-ID": OTHER_TENANT})
    assert response.status_code == 404

