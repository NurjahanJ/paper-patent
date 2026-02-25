# Ferrofluid Paper-Patent Classifier

AI-assisted classification of ~4,000 ferrofluid research papers and ~600 US patents using dual AI models (GPT-4o + Claude), with gap analysis to find where research exists but patents don't (and vice versa).

## What It Does

| Goal | Description |
|------|-------------|
| **Goal 1** | Classify all **papers** into the 30 predefined ferrofluid class codes (11–51) |
| **Goal 2** | Classify all **patents** the same way |
| **Goal 3** | **Gap analysis** — which classes have patents vs don't, by year. Link each patent to 3+ related papers |
| **Goal 4** | **Assignee cross-reference** — patent holders who also authored papers on the same topic |

## Taxonomy (30 Class Codes)

| Code | Major Category | Description |
|------|---------------|-------------|
| 11–16 | Material | Chemistry, Formulation, Properties, Evaluation, Manipulation, Handling |
| 21–29 | Computation | FEA, CFD, MATLAB, Modelling, Flow, Heat, Stability, Magnetic Droplets |
| 37 | Experimentation | Other than evaluation |
| 38–49 | Application | Magnetic induction, Medical, Robotics, Geology, Flow, Heat, Bearing, Levitation, etc. |
| 50–51 | Review / Book | Survey, Book chapter |

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file:
```
OPENAI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key
```

## Workflow

### Step 1: Import Data
```bash
# Start the API server
uvicorn app.main:app --reload

# Import all CSV data (via API)
curl -X POST http://localhost:8000/documents/import
```
Or directly:
```bash
python -c "from app.services.importer import import_all; print(import_all())"
```

### Step 2: Classify Documents
```bash
# Classify all pending documents (papers + patents)
curl -X POST "http://localhost:8000/classify/"

# Or classify only papers/patents, with limits
curl -X POST "http://localhost:8000/classify/?doc_type=paper&limit=100"
curl -X POST "http://localhost:8000/classify/?doc_type=patent&limit=50"
```

### Step 3: Review Disagreements
```bash
# List documents where GPT and Claude disagreed
curl http://localhost:8000/review/pending

# Resolve a disagreement
curl -X POST http://localhost:8000/review/resolve \
  -H "Content-Type: application/json" \
  -d '{"serial_number": "P123", "primary": 11, "secondary": 13, "tertiary": 14, "note": "Material chemistry"}'
```

### Step 4: Run Analysis
```bash
# Gap analysis
curl http://localhost:8000/analysis/gaps

# Gap analysis by 5-year periods
curl http://localhost:8000/analysis/gaps/five-year

# Link patents to related papers (TF-IDF similarity)
curl -X POST http://localhost:8000/analysis/link-patents

# Cross-reference assignees
curl -X POST http://localhost:8000/analysis/crossref-assignees
```

### Step 5: Export Results
```bash
# Export everything to output/ folder
curl -X POST http://localhost:8000/export/all

# Or individually:
curl -X POST http://localhost:8000/export/papers    # classified_papers.csv
curl -X POST http://localhost:8000/export/patents   # classified_patents.csv
curl -X POST http://localhost:8000/export/gaps      # gap_analysis.csv + gap_by_5year_periods.csv
curl -X POST http://localhost:8000/export/links     # patent_paper_links.csv
curl -X POST http://localhost:8000/export/crossrefs # assignee_crossrefs.csv
```

### Step 6: Knowledge Graph
```bash
# Open in browser
curl http://localhost:8000/graph/ > graph.html
```

## Output CSV Format

Each classified CSV contains:
- **Serial Number** — document identifier
- **Year** — publication year
- **Title** — document title
- **Primary/Secondary/Tertiary Class** — numeric class codes
- **Primary/Secondary/Tertiary Desc** — human-readable descriptions
- **Reasoning** — AI justification for classification
- **GPT Primary / Claude Primary** — individual model outputs
- **Consensus Status** — `agreed` or `human_reviewed`
- All original columns preserved with `Original_` prefix

Sorted by: Year → Primary Class → Secondary Class → Tertiary Class

## Project Structure

```
paper-patent/
├── app/
│   ├── config.py              # Settings (API keys, DB path)
│   ├── db.py                  # SQLite database layer
│   ├── main.py                # FastAPI application
│   ├── taxonomy.py            # 30 ferrofluid class codes
│   ├── models/
│   ├── routes/
│   │   ├── analysis.py        # Gap analysis + linking endpoints
│   │   ├── classify.py        # Classification pipeline endpoint
│   │   ├── documents.py       # Import + document CRUD
│   │   ├── export.py          # CSV export endpoints
│   │   ├── graph.py           # Knowledge graph endpoint
│   │   └── review.py          # Human review endpoint
│   └── services/
│       ├── classifier.py      # GPT + Claude classifiers
│       ├── consensus.py       # Agreement checker
│       ├── export.py          # CSV export logic
│       ├── gap_analysis.py    # Gap analysis logic
│       ├── importer.py        # CSV data import
│       ├── knowledge_graph.py # Graph visualization
│       ├── linking.py         # Patent-paper linking + assignee crossref
│       └── pipeline.py        # Classification orchestrator
├── data/                      # Raw CSV files
├── info/                      # Assignment docs + taxonomy definition
├── output/                    # Generated CSV exports
└── tests/                     # 23 unit tests
```

## Running Tests

```bash
python -m pytest tests/ -v
```
