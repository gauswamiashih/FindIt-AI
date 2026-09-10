"""
Similarity Service
Calculates cosine similarity vectors and computes weighted combined scores.
"""

import numpy as np
from typing import Optional, List, Dict, Any
from app.core.config import settings

class SimilarityService:
    def __init__(
        self, 
        image_weight: float = 0.75, 
        text_weight: float = 0.25,
        default_threshold: float = settings.SIMILARITY_THRESHOLD
    ):
        self.image_weight = image_weight
        self.text_weight = text_weight
        self.default_threshold = default_threshold

    def cosine_similarity(self, vector1: np.ndarray, vector2: np.ndarray) -> float:
        """
        Compute cosine similarity between two 1D or 2D feature vectors.
        Returns a float normalized between 0.0 and 1.0.
        """
        v1 = vector1.flatten()
        v2 = vector2.flatten()
        
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 < 1e-8 or norm2 < 1e-8:
            return 0.0

        sim = dot_product / (norm1 * norm2)
        # Normalize CLIP cosine similarity from [-1.0, 1.0] range to [0.0, 1.0] range
        sim_normalized = max(0.0, min(1.0, float((sim + 1.0) / 2.0)))
        return round(sim_normalized, 4)

    def compute_combined_score(
        self,
        image_similarity: float,
        text_similarity: Optional[float] = None,
        image_weight: Optional[float] = None,
        text_weight: Optional[float] = None
    ) -> float:
        """
        Compute weighted combined match score.
        Formula: combined_score = (image_weight * image_sim) + (text_weight * text_sim)
        """
        w_img = image_weight if image_weight is not None else self.image_weight
        w_txt = text_weight if text_weight is not None else self.text_weight

        if text_similarity is not None and text_similarity > 0:
            combined = (image_similarity * w_img) + (text_similarity * w_txt)
        else:
            combined = image_similarity

        return round(max(0.0, min(1.0, combined)), 4)

    def is_match(self, combined_score: float, threshold: Optional[float] = None) -> bool:
        """
        Evaluate if combined similarity score meets or exceeds the match threshold.
        """
        thresh = threshold if threshold is not None else self.default_threshold
        return combined_score >= thresh

similarity_service = SimilarityService()
