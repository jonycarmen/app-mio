from io import BytesIO

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_upload_pdf():
    person = client.post(
        "/api/people",
        json={"full_name": "Marta Sol", "dni": "888", "passport": "PA8", "bank_accounts": [], "wallet_addresses": []},
    ).json()
    person_id = person["id"]
    response = client.post(
        f"/api/people/{person_id}/documents",
        files={"file": ("receipt.pdf", BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        data={"category": "recibo", "description": "Documento de prueba"},
    )
    assert response.status_code == 201
    list_response = client.get(f"/api/people/{person_id}/documents")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_public_form_flow():
    person = client.post(
        "/api/people",
        json={"full_name": "Portal User", "dni": None, "passport": None, "bank_accounts": [], "wallet_addresses": []},
    ).json()
    token = person["access_token"]

    page_response = client.get(f"/form/{token}")
    assert page_response.status_code == 200
    assert "Portal User" in page_response.text

    update_response = client.put(
        f"/form/{token}",
        json={
            "dni": "XYZ123",
            "passport": "PASS-NEW",
            "bank_accounts": [{"bank_name": "Banco Móvil", "iban": "ES2200", "account_number": None, "notes": None}],
            "wallet_addresses": [{"network": "BTC", "address": "bc1portal", "label": "principal", "notes": None}],
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["dni"] == "XYZ123"
    assert len(update_response.json()["bank_accounts"]) == 1

    upload_response = client.post(
        f"/form/{token}/documents",
        files={"file": ("portal.pdf", BytesIO(b"%PDF-1.4 public"), "application/pdf")},
        data={"category": "self-service", "description": "Subido por el portal"},
    )
    assert upload_response.status_code == 201
    document_id = upload_response.json()["id"]

    list_response = client.get(f"/form/{token}/documents")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    file_response = client.get(f"/form/{token}/documents/{document_id}/file")
    assert file_response.status_code == 200
    assert file_response.headers["content-type"] == "application/pdf"