import csv
import os
import tempfile

import pytest

from app import db
from app.config import settings
from app.services.importer import import_csv, CsvMapping, _clean_str, _clean_int


@pytest.fixture(autouse=True)
def temp_db(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    monkeypatch.setattr(settings, "db_path", tmp.name)
    db.init_db()
    yield tmp.name
    os.unlink(tmp.name)


PAPER_MAPPING = CsvMapping(
    doc_type="paper",
    serial_prefix="P",
    authors_column="Authors",
    authors_delimiter=",",
    year_column="Year",
    source_column="Source title",
)


def _write_csv(rows: list[dict], path: str):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


class TestCleanHelpers:
    def test_clean_str_normal(self):
        assert _clean_str("hello") == "hello"

    def test_clean_str_nan(self):
        assert _clean_str(float("nan")) is None

    def test_clean_str_empty(self):
        assert _clean_str("") is None
        assert _clean_str("   ") is None

    def test_clean_str_nan_string(self):
        assert _clean_str("nan") is None

    def test_clean_int_normal(self):
        assert _clean_int(2020) == 2020
        assert _clean_int("2020") == 2020
        assert _clean_int(2020.5) == 2020

    def test_clean_int_nan(self):
        assert _clean_int(float("nan")) is None

    def test_clean_int_bad(self):
        assert _clean_int("abc") is None


class TestImportCsv:
    def test_basic_import(self, tmp_path):
        csv_file = str(tmp_path / "papers.csv")
        _write_csv([
            {"#": "1", "Title": "Paper One", "Abstract": "About ferrofluids", "Authors": "A, B", "Year": "2020", "Source title": "J1"},
            {"#": "2", "Title": "Paper Two", "Abstract": "About magnets", "Authors": "C", "Year": "2021", "Source title": "J2"},
        ], csv_file)

        result = import_csv(csv_file, PAPER_MAPPING)
        assert result["imported"] == 2
        assert result["skipped"] == 0

        docs = db.get_documents("paper")
        assert len(docs) == 2

    def test_skips_missing_abstract(self, tmp_path):
        csv_file = str(tmp_path / "papers.csv")
        _write_csv([
            {"#": "1", "Title": "Paper One", "Abstract": "Has abstract", "Authors": "A", "Year": "2020", "Source title": "J1"},
            {"#": "2", "Title": "No Abstract", "Abstract": "", "Authors": "B", "Year": "2021", "Source title": "J2"},
        ], csv_file)

        result = import_csv(csv_file, PAPER_MAPPING)
        assert result["imported"] == 1
        assert result["skipped"] == 1

    def test_deduplicates_by_title(self, tmp_path):
        csv_file = str(tmp_path / "papers.csv")
        _write_csv([
            {"#": "1", "Title": "Same Title", "Abstract": "First", "Authors": "A", "Year": "2020", "Source title": "J1"},
            {"#": "2", "Title": "Same Title", "Abstract": "Second", "Authors": "B", "Year": "2021", "Source title": "J2"},
        ], csv_file)

        result = import_csv(csv_file, PAPER_MAPPING)
        assert result["imported"] == 1
        assert result["skipped"] == 1

    def test_case_insensitive_dedup(self, tmp_path):
        csv_file = str(tmp_path / "papers.csv")
        _write_csv([
            {"#": "1", "Title": "Ferrofluid Analysis", "Abstract": "abc", "Authors": "A", "Year": "2020", "Source title": "J1"},
            {"#": "2", "Title": "FERROFLUID ANALYSIS", "Abstract": "def", "Authors": "B", "Year": "2021", "Source title": "J2"},
        ], csv_file)

        result = import_csv(csv_file, PAPER_MAPPING)
        assert result["imported"] == 1

    def test_preserves_original_data(self, tmp_path):
        csv_file = str(tmp_path / "papers.csv")
        _write_csv([
            {"#": "1", "Title": "Test", "Abstract": "abc", "Authors": "A", "Year": "2020", "Source title": "J1"},
        ], csv_file)

        import_csv(csv_file, PAPER_MAPPING)
        doc = db.get_document("P1")
        assert doc is not None
        import json
        original = json.loads(doc["original_data"])
        assert "Title" in original
        assert "Authors" in original

    def test_single_transaction_for_batch(self, tmp_path):
        """All rows in one CSV should be written in a single transaction."""
        csv_file = str(tmp_path / "papers.csv")
        _write_csv([
            {"#": str(i), "Title": f"Paper {i}", "Abstract": f"abs {i}", "Authors": "A", "Year": "2020", "Source title": "J1"}
            for i in range(50)
        ], csv_file)

        result = import_csv(csv_file, PAPER_MAPPING)
        assert result["imported"] == 50

        counts = db.count_documents()
        assert counts["papers"] == 50
