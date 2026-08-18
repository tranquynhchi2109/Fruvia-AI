#!/usr/bin/env python3
"""
Fruvia AI — Knowledge Base Coverage Audit Tool

Audits all retrievable canonical fruit classes in Qdrant Cloud against
the backend Fruit Knowledge Base to ensure 100% coverage.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from app.services.fruit_service import get_fruit_knowledge_service
from app.utils.class_resolver import resolve_class_names
from app.utils.file_utils import load_class_mapping
from qdrant_client import QdrantClient


def audit_coverage() -> None:
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    collection_name = os.getenv("QDRANT_COLLECTION", "fruvia_fruits360_original_dinov2_base_v1")

    if not url or not api_key:
        print("[ERROR] QDRANT_URL or QDRANT_API_KEY environment variables missing.", file=sys.stderr)
        sys.exit(1)

    print(f"Connecting to Qdrant Cloud collection '{collection_name}'...")
    client = QdrantClient(url=url, api_key=api_key)

    mapping = load_class_mapping(PROJECT_ROOT / "configs" / "class_mapping.yaml")
    kb_service = get_fruit_knowledge_service()
    kb_classes = set(kb_service.list_canonical_classes())

    offset = None
    total_vectors = 0
    original_classes = set()
    canonical_classes = set()

    while True:
        res, next_offset = client.scroll(
            collection_name=collection_name,
            limit=10000,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        total_vectors += len(res)
        for point in res:
            payload = point.payload or {}
            ds = payload.get("dataset_name") or payload.get("source_dataset") or "fruits-360-original-size"
            orig = payload.get("original_class") or "unknown"
            c_p = payload.get("canonical_class")
            if c_p and str(c_p).strip():
                canon = str(c_p).strip().lower()
            else:
                canon, _ = resolve_class_names(orig, mapping, ds)

            original_classes.add(orig)
            canonical_classes.add(canon)

        if not next_offset or next_offset == offset:
            break
        offset = next_offset

    covered = canonical_classes.intersection(kb_classes)
    missing = sorted(list(canonical_classes - kb_classes))
    coverage_pct = (len(covered) / len(canonical_classes) * 100.0) if canonical_classes else 0.0

    print("\n=== Fruvia Knowledge Coverage Audit ===")
    print(f"Qdrant vectors scanned: {total_vectors:,}")
    print(f"Unique original classes: {len(original_classes)}")
    print(f"Unique canonical classes: {len(canonical_classes)}")
    print(f"Knowledge records in KB: {len(kb_classes)}")
    print(f"Covered classes: {len(covered)}")
    print(f"Missing classes: {len(missing)}")
    print(f"Coverage: {coverage_pct:.2f}%")

    if missing:
        print("\nMissing Canonical Classes:")
        for m in missing:
            print(f"  - {m}")
        sys.exit(1)
    else:
        print("\nSUCCESS: 100% Knowledge Base coverage achieved across all Qdrant vectors!")


if __name__ == "__main__":
    audit_coverage()
