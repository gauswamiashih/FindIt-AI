"""
Similarity Service (Disabled for Free Tier)
"""

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

    def cosine_similarity(self, vector1: any, vector2: any) -> float:
        return 0.0

    def compute_combined_score(
        self,
        image_similarity: float,
        text_similarity: Optional[float] = None,
        image_weight: Optional[float] = None,
        text_weight: Optional[float] = None
    ) -> float:
        return 0.0

    def is_match(self, combined_score: float, threshold: Optional[float] = None) -> bool:
        return False

similarity_service = SimilarityService()

