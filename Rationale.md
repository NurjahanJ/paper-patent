# Rationale Statement (Project-Level)

## Purpose
This project classifies ferrofluid papers and patents into Professor Mani's predefined class codes to enable trend analysis, patent gap analysis, and patent-paper linking.

Reference: `AI_CLASSIFICATON_IS421_2026S`

## Why AI classification
Manual classification across thousands of documents is slow and inconsistent. Large language models can read abstracts quickly and apply consistent labeling when given clear definitions and constraints.

## Why two models + human review
Two independent model outputs reduce single-model bias. If both models agree, confidence is higher; if they disagree, the item is flagged for human review to ensure correctness and transparency.

## Why abstract-only
The assignment requires classification to be based entirely on abstract content, not titles/keywords.

Implementation verification in this codebase:
- The prompt explicitly instructs: use ONLY abstract text and do NOT use title/keywords.
- Only `abstract` is passed into model calls.
- `title` is not passed into model calls.

Reference: `AI_CLASSIFICATON_IS421_2026S`

## How patents are linked to papers
Patents are linked to at least 3 related papers using text similarity over abstracts to support the relational dependency analysis.

Reference: `AI_CLASSIFICATON_IS421_2026S`

## Taxonomy usage
The classifier uses the provided class definitions (11-51) without changing meanings unless explicitly documented.

Reference: `FEROFLUIDS_CLASS_DEFINITION`
