#!/usr/bin/env python3
"""
Fruvia Classifier Diagnostic & Debug Tool.

Audits model state, inspects Qdrant class distribution, and performs
verbose per-neighbor diagnostic inference on query images.

Usage:
    python scripts/diagnose_classifier.py
    python scripts/diagnose_classifier.py --audit-distribution
    python scripts/diagnose_classifier.py --image path/to/fruit.jpg --verbose
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add backend directory to sys.path
project_root = Path(__file__).resolve().parents[1]
backend_dir = project_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from PIL import Image

from app.core.config import get_settings
from app.ml.classifier import get_fruit_classifier
from app.ml.image_encoder import get_image_encoder
from app.repositories.qdrant_repository import get_qdrant_repository


def run_diagnostics(
    image_path: str | None = None,
    verbose: bool = False,
    audit_distribution: bool = False,
) -> None:
    """Run diagnostic audit and optional image neighbor analysis."""
    settings = get_settings()
    classifier = get_fruit_classifier()
    classifier.load_model()

    info = classifier.get_audit_info()

    print("=== Fruvia Classifier Diagnostic ===")
    print(f"Project root:         {project_root}")
    print(f"Model path:           {info['artifact_path']}")
    print(f"Exists:               {info['artifact_exists']}")
    print(f"Artifact format:      {info['artifact_type']}")
    print(f"Architecture:         {info['architecture']}")
    print(f"Classes:              {info['classes_count']} (Canonical order)")
    print(f"Preprocessing:        {info['preprocessing_source']}")
    print(f"Device:               {info['device']}")
    print(f"Inference engine:     {info['model_source']}")
    print(f"Ready:                {info['ready']} ({'via kNN Fallback' if info['is_fallback'] else 'Trained Model'})")
    print()

    if audit_distribution:
        print("=== Qdrant Collection Class Distribution ===")
        qdrant = get_qdrant_repository()
        if not qdrant.is_connected():
            print("ERROR: Qdrant Cloud is not reachable.")
        else:
            dist = qdrant.get_class_distribution()
            total_points = sum(dist.values())
            print(f"Collection: {qdrant.collection_name}")
            print(f"Total indexed points: {total_points}")
            print("-" * 50)
            for cls, count in dist.items():
                pct = (count / total_points * 100) if total_points > 0 else 0
                bar = "#" * int(pct / 2)
                print(f"  {cls:<15} : {count:>5} ({pct:>5.1f}%) {bar}")
            print()

    if image_path:
        img_file = Path(image_path)
        if not img_file.exists():
            print(f"ERROR: Image file '{image_path}' does not exist.")
            sys.exit(1)

        print(f"=== Image Analysis: {img_file.name} ===")
        try:
            image = Image.open(img_file)
            encoder = get_image_encoder()
            if not encoder.is_loaded:
                encoder.load_model()

            embedding = encoder.encode_image(image)
            norm = sum(x * x for x in embedding) ** 0.5
            print(f"Embedding dimensions: {len(embedding)}")
            print(f"Embedding L2 norm:   {norm:.4f}")

            qdrant = get_qdrant_repository()
            raw_hits = qdrant.query_similar(embedding, top_k=20)

            if verbose:
                print("\n--- TOP-20 RAW QDRANT NEIGHBORS ---")
                print(f"{'Rank':<5} | {'Original Class':<25} | {'Canonical':<15} | {'Sim':<7} | {'Filename'}")
                print("-" * 80)
                class_counts: dict[str, int] = {}
                class_sims: dict[str, list[float]] = {}

                for idx, hit in enumerate(raw_hits, 1):
                    orig = hit.original_class
                    canon = hit.canonical_class
                    sim = hit.similarity
                    fname = hit.filename
                    print(f"#{idx:<4} | {orig:<25} | {canon:<15} | {sim:<7.4f} | {fname}")

                    class_counts[canon] = class_counts.get(canon, 0) + 1
                    class_sims.setdefault(canon, []).append(sim)

                print("\n--- NEIGHBOR CLASS HISTOGRAM (Top-20) ---")
                for canon, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True):
                    sims = class_sims[canon]
                    max_sim = max(sims)
                    avg_sim = sum(sims) / len(sims)
                    print(f"  {canon:<15} : {count:>2}/20 hits | Max Sim: {max_sim:.4f} | Avg Sim: {avg_sim:.4f}")

            result = classifier.predict(image, top_k=5)
            predictions = result["predictions"]

            print("\n--- FINAL PREDICTIONS ---")
            for idx, (cls, conf) in enumerate(predictions, 1):
                print(f"  {idx}. {cls:<15} {conf * 100:>6.2f}%")

            print(f"\nInference method: {result['inference_method']}")
            print(f"Is fallback:      {result['is_fallback']}")

        except Exception as e:
            print(f"ERROR during classification: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fruvia Fruit Classifier Diagnostic Tool")
    parser.add_argument(
        "--image",
        type=str,
        default=None,
        help="Optional path to a test image file to run classification on",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable detailed top-20 neighbor dump and histogram",
    )
    parser.add_argument(
        "--audit-distribution",
        action="store_true",
        help="Audit Qdrant collection class distribution",
    )
    args = parser.parse_args()
    run_diagnostics(
        image_path=args.image,
        verbose=args.verbose,
        audit_distribution=args.audit_distribution,
    )


if __name__ == "__main__":
    main()
