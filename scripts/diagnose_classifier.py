#!/usr/bin/env python3
"""
Fruvia Classifier Diagnostic Tool.

Audits the fruit classification system setup, checks model artifacts,
preprocessing, class mapping, device, and optionally runs inference on a test image.

Usage:
    python scripts/diagnose_classifier.py
    python scripts/diagnose_classifier.py --image path/to/fruit.jpg
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add backend directory to sys.path to enable app imports
project_root = Path(__file__).resolve().parents[1]
backend_dir = project_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from PIL import Image

from app.core.config import get_settings
from app.ml.classifier import get_fruit_classifier


def run_diagnostics(image_path: str | None = None) -> None:
    """Run full diagnostic audit of FruitClassifier."""
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

    if image_path:
        img_file = Path(image_path)
        if not img_file.exists():
            print(f"ERROR: Image file '{image_path}' does not exist.")
            sys.exit(1)

        print(f"Running inference on test image: {img_file}")
        try:
            image = Image.open(img_file)
            result = classifier.predict(image, top_k=5)
            predictions = result["predictions"]

            print("\nTop predictions:")
            for idx, (cls, conf) in enumerate(predictions, 1):
                print(f"  {idx}. {cls:<15} {conf * 100:>6.2f}%")

            print(f"\nInference method: {result['inference_method']}")
            print(f"Is fallback:      {result['is_fallback']}")

        except Exception as e:
            print(f"ERROR during classification: {e}")
            sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fruvia Fruit Classifier Diagnostic Tool")
    parser.add_argument(
        "--image",
        type=str,
        default=None,
        help="Optional path to a test image file to run classification on",
    )
    args = parser.parse_args()
    run_diagnostics(image_path=args.image)


if __name__ == "__main__":
    main()
