# Fruvia AI

AI-powered fruit image similarity retrieval system using DINOv2 embeddings and Qdrant vector search.

## Project Goal

Fruvia AI provides a single core feature:

- **Image Retrieval** — Upload an image to find visually similar fruit images via vector search using DINOv2 768-dim embeddings and Qdrant Cloud vector database (`fruvia_fruits360_original_dinov2_base_v1`).

## System Architecture

```
Frontend
   ↓
POST /api/retrieve
   ↓
FastAPI
   ↓
DINOv2 Image Encoder
   ↓
768-dimensional normalized embedding
   ↓
Qdrant Cloud
   ↓
Top-K similar fruit images
```

### Retrieval Flow

```
User uploads image
    → Validate (format, size, integrity)
    → DINOv2 encode → 768-dim vector (L2 normalized)
    → Query Qdrant Cloud (cosine similarity)
    → Return Top-K similar images with similarity scores
```

## Project Structure

```
fruvia-ai/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── api/                    # Route handlers
│   │   │   ├── routes_health.py
│   │   │   └── routes_retrieval.py
│   │   ├── core/                   # Config, logging, exceptions
│   │   ├── ml/                     # DINOv2 encoder, preprocessing
│   │   ├── services/               # Business logic (retrieval service)
│   │   ├── repositories/           # Data access (Qdrant)
│   │   ├── schemas/                # Pydantic request/response models
│   │   └── utils/                  # Image validation, file helpers
│   ├── tests/
│   │   ├── unit/                   # Unit test suite
│   │   └── integration/            # Integration test suite
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                       # Static HTML/CSS/JS UI
├── notebooks/                      # Colab notebooks for DINOv2 & Qdrant
├── configs/                        # YAML configuration
├── .env.example                    # Environment variable template
├── docker-compose.yml
├── pyproject.toml
└── Makefile
```

## Getting Started

### Prerequisites

- Python 3.10+
- pip

### Local Setup

```bash
# Clone repository
git clone https://github.com/tranquynhchi2109/Fruvia-AI.git
cd Fruvia-AI

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r backend/requirements.txt

# Copy environment config
cp .env.example .env
# Edit .env with your Qdrant Cloud credentials
```

### Run Backend

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Or use Make:

```bash
make run-backend
```

### Run Frontend

In a separate terminal, serve the static frontend directory:

```bash
python -m http.server 3000 --directory frontend
```

Open your browser at:
- **Landing page**: [http://localhost:3000](http://localhost:3000)
- **Image Retrieval Web UI**: [http://localhost:3000/retrieval.html](http://localhost:3000/retrieval.html)

Or use Make:

```bash
make run-frontend
```

### Run Tests

```bash
pytest backend/tests -v
```

## License

MIT
