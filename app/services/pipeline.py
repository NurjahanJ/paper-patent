import asyncio
import logging
import time
from typing import Optional

from app import db
from app.db.connection import transaction
from app.config import settings
from app.services.classifier import (
    BaseClassifier,
    ClassificationError,
    ClaudeClassifier,
    GPTClassifier,
)
from app.services.consensus import check_consensus
from app.services.rate_limiter import TokenBucketRateLimiter

logger = logging.getLogger(__name__)


async def classify_one(
    doc: dict,
    gpt: BaseClassifier,
    claude: BaseClassifier,
    retries: int = 3,
) -> bool:
    """Classify a single document with both models. Returns True on success."""
    serial = doc["serial_number"]
    abstract = doc["abstract"]

    for attempt in range(1, retries + 1):
        try:
            gpt_result, claude_result = await asyncio.gather(
                gpt.classify(abstract),
                claude.classify(abstract),
            )

            final = check_consensus(gpt_result, claude_result)

            # Atomic: save both AI results + final classification in one transaction
            with transaction() as conn:
                db.save_ai_result(serial, "gpt",
                                  gpt_result["primary"], gpt_result["secondary"],
                                  gpt_result["tertiary"], gpt_result["reasoning"],
                                  conn=conn)
                db.save_ai_result(serial, "claude",
                                  claude_result["primary"], claude_result["secondary"],
                                  claude_result["tertiary"], claude_result["reasoning"],
                                  conn=conn)
                db.finalize_classification(serial, final["primary"], final["secondary"],
                                           final["tertiary"], final["reasoning"],
                                           final["status"], conn=conn)
            return True

        except ClassificationError as e:
            logger.warning("Attempt %d/%d failed for %s: %s", attempt, retries, serial, e)
            if attempt < retries:
                await asyncio.sleep(2 ** attempt)
            else:
                logger.error("All %d attempts failed for %s", retries, serial)
                return False
        except Exception as e:
            logger.error("Unexpected error for %s: %s", serial, e)
            if attempt < retries:
                await asyncio.sleep(2 ** attempt)
            else:
                return False

    return False


async def run_classification(
    doc_type: Optional[str] = None,
    concurrency: Optional[int] = None,
    limit: Optional[int] = None,
) -> dict:
    """
    Run the full classification pipeline.
    - Resumes from where it left off (skips already-classified docs).
    - Runs with bounded concurrency.
    - Tracks progress.
    """
    if concurrency is None:
        concurrency = settings.concurrency

    # Rate limiters based on actual API tier limits (with 10% safety margin)
    # OpenAI: 30,000 TPM -> use 27,000
    # Anthropic: 540,000 TPM -> use 480,000
    gpt_limiter = TokenBucketRateLimiter(capacity=27_000, window_seconds=60.0)
    claude_limiter = TokenBucketRateLimiter(capacity=480_000, window_seconds=60.0)

    gpt = GPTClassifier(api_key=settings.openai_api_key, rate_limiter=gpt_limiter)
    claude = ClaudeClassifier(api_key=settings.anthropic_api_key, rate_limiter=claude_limiter)

    docs = db.get_unclassified_documents(doc_type)
    if limit:
        docs = docs[:limit]

    total = len(docs)
    if total == 0:
        logger.info("No documents to classify.")
        return {"total": 0, "success": 0, "failed": 0, "time_seconds": 0}

    logger.info("Starting classification: %d documents, concurrency=%d", total, concurrency)

    success = 0
    failed = 0
    start_time = time.time()

    # Process in fixed-size batches to prevent task pile-up on rate limits
    for batch_start in range(0, total, concurrency):
        batch = docs[batch_start:batch_start + concurrency]

        results = await asyncio.gather(
            *[classify_one(doc, gpt, claude) for doc in batch],
            return_exceptions=True,
        )

        for r in results:
            if r is True:
                success += 1
            else:
                failed += 1

        done = success + failed
        elapsed = time.time() - start_time
        rate = done / elapsed if elapsed > 0 else 0
        eta = (total - done) / rate if rate > 0 else 0
        logger.info(
            "Progress: %d/%d (%.1f%%) | %.1f docs/min | ETA: %.0f min | ok=%d err=%d",
            done, total, 100 * done / total,
            rate * 60, eta / 60,
            success, failed,
        )

    elapsed = time.time() - start_time
    result = {
        "total": total,
        "success": success,
        "failed": failed,
        "time_seconds": round(elapsed, 1),
    }
    logger.info("Classification complete: %s", result)
    return result
