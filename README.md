# Ferrofluid Paper-Patent Classifier

AI-assisted classification of ~4,000 ferrofluid research papers and ~600 US patents using dual AI models (GPT-4o + Claude), with gap analysis to find where research exists but patents don't (and vice versa).

## What It Does

| Goal | Description |
|------|-------------|
| **Goal 1** | Classify all **papers** into the 30 predefined ferrofluid class codes (11–51) |
| **Goal 2** | Classify all **patents** the same way |
| **Goal 3** | **Gap analysis** — which classes have patents vs don't, by year. Link each patent to 3+ related papers |
| **Goal 4** | **Assignee cross-reference** — patent holders who also authored papers on the same topic |

## Separate Rationale Statement

See [`Rationale.md`](./Rationale.md) for the project-level rationale (purpose, abstract-only classification basis, two-model + human review justification, linking rationale, and taxonomy usage).

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

## Dashboard

### Quick Start: View the Dashboard

```bash
# Start the server
uvicorn app.main:app --host 127.0.0.1 --port 8000

# Open in browser
# Navigate to: http://127.0.0.1:8000/dashboard
```

The dashboard provides:
- **Overview** — Classification statistics and progress
- **Results & Findings** — Summary of all analyses
- **Classified Papers/Patents** — Browse and filter classified documents
- **Gap Analysis** — Visualize research gaps by class and time period
- **Review Disagreements** — Resolve AI classification conflicts with improved UI
- **Knowledge Graph** — Interactive visualization of paper-patent relationships

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
│   ├── config.py              # Settings (API keys, DB path, rate limits)
│   ├── main.py                # FastAPI application
│   ├── taxonomy.py            # 30 ferrofluid class codes
│   ├── db/                    # SQLite database layer (modular)
│   │   ├── connection.py      # Connection + transaction context manager
│   │   ├── documents.py       # Document CRUD
│   │   ├── classifications.py # Classification + AI result CRUD
│   │   └── links.py           # Patent-paper links + crossrefs
│   ├── routes/
│   │   ├── analysis.py        # Gap analysis + linking endpoints
│   │   ├── classify.py        # Classification pipeline endpoint
│   │   ├── documents.py       # Import + document CRUD
│   │   ├── export.py          # CSV export endpoints
│   │   ├── graph.py           # Knowledge graph endpoint
│   │   ├── progress.py        # Live progress dashboard API
│   │   ├── review.py          # Human review API
│   │   └── review_ui.py       # Review disagreements UI
│   ├── services/
│   │   ├── classifier.py      # GPT + Claude classifiers
│   │   ├── consensus.py       # Agreement checker
│   │   ├── export.py          # CSV export logic
│   │   ├── gap_analysis.py    # Gap analysis logic
│   │   ├── importer.py        # CSV data import
│   │   ├── knowledge_graph.py # Graph visualization
│   │   ├── linking.py         # Patent-paper linking + assignee crossref
│   │   ├── pipeline.py        # Classification orchestrator
│   │   └── rate_limiter.py    # Token-bucket rate limiter for API calls
│   └── templates/             # HTML templates for dashboards
│       ├── progress.html      # Live classification progress
│       └── review_ui.html     # Disagreement review UI
├── data/                      # Raw CSV files
├── info/                      # Assignment docs + taxonomy definition
├── output/                    # Generated CSV exports
├── scripts/                   # Utility scripts
└── tests/                     # 50 unit tests
```

## Deployment to Render.com

### Prerequisites
1. Push your code to GitHub
2. Create a Render.com account and connect it to GitHub

### Deploy Steps

1. **Push to GitHub:**
   ```bash
   git push origin deploy-render
   ```

2. **On Render.com Dashboard:**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Render will auto-detect `render.yaml` and configure everything

3. **Set Environment Variables:**
   - In Render dashboard, go to your service → Environment
   - Add:
     - `OPENAI_API_KEY` = your OpenAI API key
     - `ANTHROPIC_API_KEY` = your Anthropic API key

4. **Deploy:**
   - Render will automatically build and deploy
   - Your dashboard will be live at: `https://your-app-name.onrender.com/dashboard`

### Important Notes
- **Free tier limitations:**
  - Service spins down after 15 minutes of inactivity
  - First request after sleep takes ~30 seconds (cold start)
  - 750 hours/month free (enough for most use cases)
- **Database:** SQLite persists on the 1GB disk volume
- **Auto-deploy:** Pushes to your branch trigger automatic redeployment

### Local Development
The app works the same locally. See [Dashboard](#dashboard) section above.

## Running Tests

```bash
python -m pytest tests/ -v
```
