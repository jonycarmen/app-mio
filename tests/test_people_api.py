from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_people_crud_flow():
    create_response = client.post(
        "/api/people",
        json={
            "full_name": "Ana Perez",
            "dni": "12345678A",
            "passport": "P1234",
            "bank_accounts": [{"bank_name": "Banco Uno", "iban": "ES11"}],
            "wallet_addresses": [{"network": "ETH", "address": "0xabc"}],
        },
    )
    assert create_response.status_code == 201
    created_person = create_response.json()
    person_id = created_person["id"]
    assert created_person["access_token"]

    list_response = client.get("/api/people")
    assert list_response.status_code == 200
    assert list_response.json()[0]["full_name"] == "Ana Perez"
    assert list_response.json()[0]["access_token"]

    detail_response = client.get(f"/api/people/{person_id}")
    assert detail_response.status_code == 200
    assert len(detail_response.json()["bank_accounts"]) == 1


def test_regenerate_person_token():
    person = client.post(
        "/api/people",
        json={
            "full_name": "Luis Token",
            "dni": "7777",
            "passport": "PASS7777",
            "bank_accounts": [],
            "wallet_addresses": [],
        },
    ).json()

    original_token = person["access_token"]
    response = client.post(f"/api/people/{person['id']}/regenerate-token")

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["access_token"] != original_token