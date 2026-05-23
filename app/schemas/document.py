from datetime import datetime

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: int
    person_id: int
    original_filename: str
    mime_type: str
    file_size: int
    category: str | None = None
    description: str | None = None
    uploaded_at: datetime

    model_config = {"from_attributes": True}