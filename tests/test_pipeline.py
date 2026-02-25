import asyncio
import os
import tempfile

import pytest

from app import db
from app.config import settings
from app.services.classifier import BaseClassifier, ClassificationError
from app.services.pipeline import classify_one, run_classification


@pytest.fixture(autouse=True)
def temp_db(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    monkeypatch.setattr(settings, "db_path", tmp.name)
    db.init_db()
    yield tmp.name
    os.unlink(tmp.name)


class FakeClassifier(BaseClassifier):
    """Returns a fixed classification result."""
    def __init__(self, primary=11, secondary=13, tertiary=14, reasoning="fake"):
        self._result = {
            "primary": primary,
            "secondary": secondary,
            "tertiary": tertiary,
            "reasoning": reasoning,
        }

    async def classify(self, abstract: str) -> dict:
        return self._result


class FailingClassifier(BaseClassifier):
    """Always raises ClassificationError."""
    async def classify(self, abstract: str) -> dict:
        raise ClassificationError("Simulated API failure")


class TestClassifyOne:
    def test_agreement(self):
        db.insert_document("P1", "paper", "Test", "abstract text", 2020, [], None, {})
        doc = db.get_document("P1")

        gpt = FakeClassifier(primary=11, secondary=13, tertiary=14, reasoning="gpt says material")
        claude = FakeClassifier(primary=11, secondary=12, tertiary=14, reasoning="claude says material")

        ok = asyncio.get_event_loop().run_until_complete(
            classify_one(doc, gpt, claude, retries=1)
        )
        assert ok is True

        c = db.get_classification("P1")
        assert c is not None
        assert c["status"] == "agreed"
        assert c["final_primary"] == 11
        assert c["gpt_primary"] == 11
        assert c["claude_primary"] == 11

    def test_disagreement(self):
        db.insert_document("P2", "paper", "Test2", "abstract text", 2020, [], None, {})
        doc = db.get_document("P2")

        gpt = FakeClassifier(primary=11)
        claude = FakeClassifier(primary=38)

        ok = asyncio.get_event_loop().run_until_complete(
            classify_one(doc, gpt, claude, retries=1)
        )
        assert ok is True

        c = db.get_classification("P2")
        assert c["status"] == "disagreed"

    def test_failure_returns_false(self):
        db.insert_document("P3", "paper", "Test3", "abstract text", 2020, [], None, {})
        doc = db.get_document("P3")

        gpt = FailingClassifier()
        claude = FakeClassifier(primary=11)

        ok = asyncio.get_event_loop().run_until_complete(
            classify_one(doc, gpt, claude, retries=1)
        )
        assert ok is False

        c = db.get_classification("P3")
        assert c is None

    def test_atomic_write_on_success(self):
        """Both AI results and final classification should be saved together."""
        db.insert_document("P4", "paper", "Test4", "abstract text", 2020, [], None, {})
        doc = db.get_document("P4")

        gpt = FakeClassifier(primary=25, secondary=26, tertiary=22)
        claude = FakeClassifier(primary=25, secondary=21, tertiary=28)

        ok = asyncio.get_event_loop().run_until_complete(
            classify_one(doc, gpt, claude, retries=1)
        )
        assert ok is True

        c = db.get_classification("P4")
        assert c["gpt_primary"] == 25
        assert c["claude_primary"] == 25
        assert c["final_primary"] == 25
        assert c["status"] == "agreed"


class TestRunClassification:
    def test_skips_already_classified(self, monkeypatch):
        db.insert_document("P1", "paper", "Done", "abstract", 2020, [], None, {})
        db.insert_document("P2", "paper", "Pending", "abstract2", 2021, [], None, {})

        # Classify P1 manually
        db.save_ai_result("P1", "gpt", 11, 11, 11, "r")
        db.finalize_classification("P1", 11, 11, 11, "ok", "agreed")

        # Patch pipeline to use fakes
        monkeypatch.setattr(
            "app.services.pipeline.GPTClassifier",
            lambda **kw: FakeClassifier(primary=38),
        )
        monkeypatch.setattr(
            "app.services.pipeline.ClaudeClassifier",
            lambda **kw: FakeClassifier(primary=38),
        )

        result = asyncio.get_event_loop().run_until_complete(
            run_classification(concurrency=1)
        )
        assert result["total"] == 1  # Only P2
        assert result["success"] == 1

    def test_empty_returns_zero(self):
        result = asyncio.get_event_loop().run_until_complete(
            run_classification(concurrency=1)
        )
        assert result["total"] == 0
        assert result["success"] == 0
