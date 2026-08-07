# Fruvia AI

AI-powered fruit recognition and image retrieval system using deep learning.

## Project Goal

Fruvia AI provides two independent, fully operational AI capabilities:

1. **Fruit Classification** — Upload an image, get top-K fruit predictions with confidence scores using trained PyTorch models (ConvNeXt-Tiny / EfficientNet-B0) or DINOv2 + Qdrant 20-kNN similarity-weighted voting fallback.
2. **Image Retrieval** — Upload an image, find visually similar fruit images via vector search using DINOv2 768-dim embeddings and Qdrant Cloud vector database (`fruvia_fruits360_original_dinov2_base_v1`).

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                     Frontend                         │
│  index.html │ classify.html │ retrieval.html         │
│         HTML + CSS + Vanilla JavaScript              │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP (JSON + multipart)
┌──────────────────────▼──────────────────────────────┐
│                  FastAPI Backend                     │
│  ┌──────────┐  ┌───────────┐  ┌──────────────────┐  │
│  │  /health │  │ /classify │  │   /retrieve      │  │
│  └──────────┘  └─────┬─────┘  └────────┬─────────┘  │
│                      │                 │             │
│         ┌────────────▼───┐   ┌─────────▼──────────┐ │
│         │ FruitClassifier│   │  DINOv2 Encoder    │ │
│         │ (Multi-Engine) │   │  (768-dim vectors) │ │
│         └──────┬───────┬─┘   └─────────┬──────────┘ │
│                │       │               │             │
│   ┌────────────▼──┐ ┌──▼───────────────▼──────────┐ │
│   │ Trained Model │ │   Qdrant Repository         │ │
│   │ (ConvNeXt/    │ │ (kNN Fallback / Retrieval) │ │
│   │ EfficientNet) │ └──────────────────┬──────────┘ │
│   └───────────────┘                    │             │
└────────────────────────────────────────┼────────────┘
                                         │
                               ┌─────────▼──────────┐
                               │   Qdrant Cloud     │
                               │ (Vector Database)  │
                               │ 20-kNN Voting      │
                               └────────────────────┘
```

### Classification Engine Hierarchy

1. **Primary: Trained PyTorch Model**
   - Supports StateDict, Checkpoint Dict, Full Module, and TorchScript (`.pth`, `.pt`).
   - Architectures: `convnext_tiny`, `efficientnet_b0`, `mobilenet_v3_small`.
   - Validated against canonical 18 target classes (`configs/classes.yaml`).

2. **Fallback: DINOv2 + Qdrant 20-kNN Similarity-Weighted Voting**
   - Active when no trained model file is present in `models/classifier/`.
   - Encodes query image via DINOv2 (`facebook/dinov2-base`, 768-dim L2-normalized vector).
   - Queries Qdrant Cloud for top-20 nearest neighbors.
   - Computes similarity-weighted voting:
     $$\text{weight}(c) = \sum \max(\text{similarity} - 0.35, 0)$$
   - Returns normalized probability distribution and metadata (`is_fallback: true`, `inference_method: "dinov2_qdrant_knn"`).

3. **Unavailable: HTTP 503**
   - Returned if neither a trained model artifact nor Qdrant Cloud connection is ready.
   - **NO random neural network weights fallback is ever used.**

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
│   │   │   ├── routes_classification.py
│   │   │   ├── routes_retrieval.py
│   │   │   └── routes_fruits.py
│   │   ├── core/                   # Config, logging, exceptions
│   │   ├── ml/                     # ML models, classifier, encoder, preprocessing
│   │   ├── services/               # Business logic
│   │   ├── repositories/           # Data access (Qdrant)
│   │   ├── schemas/                # Pydantic request/response models
│   │   └── utils/                  # Image validation, file helpers
│   ├── tests/
│   │   ├── unit/                   # Unit test suite
│   │   └── integration/            # Integration test suite
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                       # Static HTML/CSS/JS UI
├── notebooks/                      # Colab notebooks (01–07)
├── scripts/                        # Diagnostics, dataset audit, manifest, export
│   └── diagnose_classifier.py      # CLI Diagnostic Tool
├── configs/                        # YAML configuration
│   ├── classes.yaml                # Canonical target class list (18 classes)
│   ├── class_mapping.yaml          # Original → target mapping
│   └── training.yaml               # Training hyperparameters
├── data/                           # Dataset files (not committed)
├── models/                         # Trained model artifacts
│   └── classifier/
│       ├── model.pth               # Trained PyTorch model
│       ├── model_config.json       # Architecture metadata
│       └── preprocessing.json      # Preprocessing metadata
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
git clone https://github.com/dinhvien04/fruvia-ai.git
cd fruvia-ai

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

### Run Diagnostic Audit Tool

```bash
# Audit model state and readiness
python scripts/diagnose_classifier.py

# Test classification on a sample image
python scripts/diagnose_classifier.py --image path/to/sample_fruit.jpg
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
- **Classification UI**: [http://localhost:3000/classify.html](http://localhost:3000/classify.html)
- **Image Retrieval Web UI**: [http://localhost:3000/retrieval.html](http://localhost:3000/retrieval.html)

Or use Make:

```bash
make run-frontend
```

### Run Tests

```bash
# All tests
pytest backend/tests -v
```

## License

MIT
