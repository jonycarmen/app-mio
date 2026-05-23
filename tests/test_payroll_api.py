from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_payroll_flow():
    person = client.post(
        "/api/people",
        json={"full_name": "Luis Ruiz", "dni": "999", "passport": "PX9", "bank_accounts": [], "wallet_addresses": []},
    ).json()
    person_id = person["id"]
    payroll_response = client.post(
        f"/api/people/{person_id}/payrolls",
        json={"amount": 1500, "effective_date": "2026-04-24", "notes": "Alta"},
    )
    assert payroll_response.status_code == 201
    current_response = client.get(f"/api/people/{person_id}/payrolls/current")
    assert current_response.status_code == 200
    assert current_response.json()["amount"] == "1500.00"