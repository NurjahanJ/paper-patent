# Paper-Patent Classifier

AI-assisted system for classifying patents and research abstracts into technical categories using **dual AI classification** (GPT-4o + Claude) with consensus-based validation and knowledge graph visualization.

## How It Works

1. **Add Documents** — Upload patent or research paper abstracts via the API.
2. **Dual AI Classification** — Each document is independently classified by GPT-4o and Claude.
3. **Consensus Check** — If both models agree, the classification is accepted. If they disagree, the document is flagged for human review.
4. **Human Review** — Disagreements are resolved by a human reviewer who selects the correct classification.
5. **Knowledge Graph** — Once classified, documents are visualized as an interactive knowledge graph showing relationships between patents, papers, and categories.

## Setup

### 1. Clone and install dependencies

```bash
cd paper-patent
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure API keys

Copy `.env.example` to `.env` and add your API keys:

```bash
copy .env.example .env
```

Edit `.env`:
```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Run the server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/documents/` | List all documents |
| POST | `/documents/` | Add a new document |
| GET | `/documents/{id}` | Get a specific document |
| DELETE | `/documents/{id}` | Delete a document |
| POST | `/documents/classify` | Classify pending documents (dual AI) |
| GET | `/review/pending` | List documents with classification disagreements |
| POST | `/review/resolve` | Resolve a disagreement with human decision |
| POST | `/graph/generate` | Generate interactive knowledge graph |

## Example: Add a Document

```json
POST /documents/
{
    "title": "Deep Learning for Patent Classification",
    "abstract": "This paper presents a novel approach to automated patent classification using transformer-based deep learning models...",
    "doc_type": "research_paper",
    "authors": ["John Doe", "Jane Smith"],
    "year": 2024
}
```

## Example: Classify Documents

```json
POST /documents/classify
{
    "document_ids": null
}
```

Passing `null` or omitting `document_ids` classifies all pending documents.

## Knowledge Graph

The graph uses color coding:
- 🟢 **Green diamonds** — Patents
- 🔵 **Blue circles** — Research papers
- 🟠 **Orange squares** — Categories

Generate the graph by calling `POST /graph/generate`.
