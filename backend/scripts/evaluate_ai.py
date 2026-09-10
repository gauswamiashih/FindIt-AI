"""
AI Matching Model Evaluation Script
Computes Precision, Recall, F1-score, and Precision@K for similarity matching models.

Usage:
    python scripts/evaluate_ai.py --dataset path/to/dataset.json --threshold 0.85
"""

import argparse
import json
import os
import sys
import numpy as np
from typing import List, Dict, Any, Tuple

# Insert parent path for app imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.similarity_service import similarity_service

def compute_metrics(
    ground_truth_pairs: List[Tuple[int, int]],
    predicted_pairs: List[Tuple[int, int, float]],
    threshold: float = 0.85,
    top_k: int = 5
) -> Dict[str, float]:
    """
    Calculate Precision, Recall, F1-score, and Precision@K.

    Args:
        ground_truth_pairs: List of true (lost_item_id, found_item_id) match pairs.
        predicted_pairs: List of predicted (lost_item_id, found_item_id, similarity_score).
        threshold: Score threshold for binary positive prediction.
        top_k: K rank limit for Precision@K.
    """
    gt_set = set(ground_truth_pairs)
    
    # Filter predictions above threshold
    positive_preds = [p for p in predicted_pairs if p[2] >= threshold]
    pred_set = set((p[0], p[1]) for p in positive_preds)

    true_positives = len(gt_set.intersection(pred_set))
    false_positives = len(pred_set - gt_set)
    false_negatives = len(gt_set - pred_set)

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    # Sort predicted pairs by score descending
    sorted_preds = sorted(predicted_pairs, key=lambda x: x[2], reverse=True)[:top_k]
    top_k_set = set((p[0], p[1]) for p in sorted_preds)
    precision_at_k = len(gt_set.intersection(top_k_set)) / min(top_k, len(sorted_preds)) if sorted_preds else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "precision_at_k": round(precision_at_k, 4),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }

def main():
    parser = argparse.ArgumentParser(description="Evaluate AI CLIP Similarity Matching Model")
    parser.add_argument("--dataset", type=str, help="Path to labeled evaluation dataset JSON")
    parser.add_argument("--threshold", type=float, default=0.85, help="Similarity threshold")
    parser.add_argument("--top_k", type=int, default=5, help="Top K rank limit")
    args = parser.parse_args()

    print("=" * 60)
    print("FindIt AI CLIP Similarity Matching Evaluation Framework")
    print("=" * 60)

    if not args.dataset or not os.path.exists(args.dataset):
        print("\n⚠️ NOTE ON MODEL EVALUATION:")
        print("No labeled benchmark evaluation dataset was supplied.")
        print("Model performance metrics (Precision, Recall, F1) require a human-annotated dataset of true lost/found pairs.")
        print("Formal accuracy metrics have NOT yet been calculated on a production benchmark dataset.")
        print("\nTo run evaluation once a dataset is available:")
        print("    python scripts/evaluate_ai.py --dataset data/labeled_matches.json --threshold 0.85")
        sys.exit(0)

    try:
        with open(args.dataset, "r") as f:
            data = json.load(f)
        
        gt_pairs = [tuple(p) for p in data.get("ground_truth", [])]
        pred_pairs = [tuple(p) for p in data.get("predictions", [])]

        results = compute_metrics(gt_pairs, pred_pairs, threshold=args.threshold, top_k=args.top_k)

        print("\n📊 Evaluation Results:")
        print(f"  • Precision:      {results['precision']}")
        print(f"  • Recall:         {results['recall']}")
        print(f"  • F1-Score:       {results['f1_score']}")
        print(f"  • Precision@{args.top_k}:    {results['precision_at_k']}")
        print(f"  • True Positives:  {results['true_positives']}")
        print(f"  • False Positives: {results['false_positives']}")
        print(f"  • False Negatives: {results['false_negatives']}")

    except Exception as e:
        print(f"Error during evaluation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
