import os
import tempfile

import pytest

from app import db
from app.config import settings


@pytest.fixture(autouse=True)
def temp_db(monkeypatch):
    """Use a temporary database for each test."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    monkeypatch.setattr(settings, "db_path", tmp.name)
    db.init_db()
    yield tmp.name
    os.unlink(tmp.name)


class TestDocumentCRUD:
    def test_insert_and_get(self):
        db.insert_document("P1", "paper", "Test Paper", "Abstract text",
                           2020, ["Author A"], "Journal X", {"Title": "Test Paper"})
        doc = db.get_document("P1")
        assert doc is not None
        assert doc["title"] == "Test Paper"
        assert doc["doc_type"] == "paper"
        assert doc["year"] == 2020

    def test_get_nonexistent(self):
        assert db.get_document("nope") is None

    def test_get_documents_by_type(self):
        db.insert_document("P1", "paper", "Paper 1", "abs", 2020, [], None, {})
        db.insert_document("PT1", "patent", "Patent 1", "abs", 2020, [], None, {})

        papers = db.get_documents("paper")
        assert len(papers) == 1
        assert papers[0]["serial_number"] == "P1"

        patents = db.get_documents("patent")
        assert len(patents) == 1
        assert patents[0]["serial_number"] == "PT1"

    def test_count_documents(self):
        db.insert_document("P1", "paper", "Paper 1", "abs", 2020, [], None, {})
        db.insert_document("P2", "paper", "Paper 2", "abs", 2021, [], None, {})
        db.insert_document("PT1", "patent", "Patent 1", "abs", 2020, [], None, {})

        counts = db.count_documents()
        assert counts["total"] == 3
        assert counts["papers"] == 2
        assert counts["patents"] == 1
        assert counts["pending"] == 3

    def test_unclassified_documents(self):
        db.insert_document("P1", "paper", "Paper", "abstract text", 2020, [], None, {})
        db.insert_document("P2", "paper", "Paper 2", "more text", 2021, [], None, {})

        unclass = db.get_unclassified_documents()
        assert len(unclass) == 2

        # Classify P1
        db.save_classification("P1", "gpt", 11, 13, 14, "material")
        db.save_classification("P1", "claude", 11, 12, 14, "material")
        db.finalize_classification("P1", 11, 13, 14, "agreed", "agreed")

        unclass = db.get_unclassified_documents()
        assert len(unclass) == 1
        assert unclass[0]["serial_number"] == "P2"


class TestClassificationCRUD:
    def test_save_and_get(self):
        db.insert_document("P1", "paper", "Test", "abs", 2020, [], None, {})
        db.save_classification("P1", "gpt", 11, 13, 14, "reason1")
        db.save_classification("P1", "claude", 11, 12, 14, "reason2")
        db.finalize_classification("P1", 11, 13, 14, "Both agreed", "agreed")

        c = db.get_classification("P1")
        assert c is not None
        assert c["gpt_primary"] == 11
        assert c["claude_primary"] == 11
        assert c["final_primary"] == 11
        assert c["status"] == "agreed"

    def test_get_by_status(self):
        db.insert_document("P1", "paper", "Test1", "abs", 2020, [], None, {})
        db.insert_document("P2", "paper", "Test2", "abs", 2021, [], None, {})

        db.save_classification("P1", "gpt", 11, 11, 11, "r")
        db.finalize_classification("P1", 11, 11, 11, "ok", "agreed")

        db.save_classification("P2", "gpt", 11, 11, 11, "r")
        db.finalize_classification("P2", 38, 38, 38, "disagree", "disagreed")

        agreed = db.get_classifications_by_status("agreed")
        assert len(agreed) == 1
        disagreed = db.get_classifications_by_status("disagreed")
        assert len(disagreed) == 1


class TestLinks:
    def test_save_and_get_link(self):
        db.insert_document("PT1", "patent", "Patent", "abs", 2020, [], None, {})
        db.insert_document("P1", "paper", "Paper", "abs", 2020, [], None, {})

        db.save_paper_patent_link("PT1", "P1", 0.85)
        links = db.get_links_for_patent("PT1")
        assert len(links) == 1
        assert links[0]["paper_serial"] == "P1"
        assert links[0]["similarity_score"] == 0.85

    def test_save_and_get_crossref(self):
        db.insert_document("PT1", "patent", "Patent", "abs", 2020, [], None, {})
        db.insert_document("P1", "paper", "Paper", "abs", 2020, [], None, {})

        db.save_assignee_crossref("PT1", "P1", "John Smith")
        refs = db.get_crossrefs_for_patent("PT1")
        assert len(refs) == 1
        assert refs[0]["matched_name"] == "John Smith"
