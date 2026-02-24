import json
import os
from typing import Optional

from app.config import settings
from app.models.schemas import Document


def _ensure_data_file():
    os.makedirs(os.path.dirname(settings.data_file), exist_ok=True)
    if not os.path.exists(settings.data_file):
        with open(settings.data_file, "w") as f:
            json.dump([], f)


def load_documents() -> list[Document]:
    _ensure_data_file()
    with open(settings.data_file, "r") as f:
        data = json.load(f)
    return [Document(**d) for d in data]


def save_documents(documents: list[Document]):
    _ensure_data_file()
    with open(settings.data_file, "w") as f:
        json.dump([d.model_dump(mode="json") for d in documents], f, indent=2, default=str)


def get_document_by_id(doc_id: str) -> Optional[Document]:
    documents = load_documents()
    for doc in documents:
        if doc.id == doc_id:
            return doc
    return None


def add_document(document: Document) -> Document:
    documents = load_documents()
    documents.append(document)
    save_documents(documents)
    return document


def update_document(updated: Document) -> Document:
    documents = load_documents()
    for i, doc in enumerate(documents):
        if doc.id == updated.id:
            documents[i] = updated
            break
    save_documents(documents)
    return updated


def delete_document(doc_id: str) -> bool:
    documents = load_documents()
    original_len = len(documents)
    documents = [d for d in documents if d.id != doc_id]
    if len(documents) < original_len:
        save_documents(documents)
        return True
    return False
