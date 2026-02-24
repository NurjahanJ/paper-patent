from app.models.schemas import (
    Classification,
    ClassificationStatus,
    Document,
)


def check_consensus(document: Document) -> Document:
    if not document.gpt_classification or not document.claude_classification:
        return document

    gpt = document.gpt_classification.classification
    claude = document.claude_classification.classification

    gpt_cat = gpt.category.strip().lower()
    claude_cat = claude.category.strip().lower()

    if gpt_cat == claude_cat:
        document.status = ClassificationStatus.AGREED

        avg_confidence = (gpt.confidence + claude.confidence) / 2
        merged_keywords = list(set(gpt.keywords + claude.keywords))

        subcategory = gpt.subcategory or claude.subcategory

        document.final_classification = Classification(
            category=gpt.category,
            subcategory=subcategory,
            confidence=round(avg_confidence, 3),
            keywords=merged_keywords,
        )
    else:
        document.status = ClassificationStatus.DISAGREED

    return document
