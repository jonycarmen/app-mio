from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


Path("storage/pdfs").mkdir(parents=True, exist_ok=True)


def get_client() -> TestClient:
    return TestClient(app)