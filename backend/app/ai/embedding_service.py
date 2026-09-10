"""
Embedding Service
Manages in-memory caching and vector normalization for CLIP image & text embeddings.
"""

import logging
import numpy as np
from typing import Dict, Optional, List, Tuple
from app.ai.clip_service import CLIPService

logger = logging.getLogger("findit.ai.embedding")

class EmbeddingService:
    def __init__(self):
        # In-memory LRU-like cache for image embeddings keyed by URL or hash
        self._image_cache: Dict[str, np.ndarray] = {}
        self._text_cache: Dict[str, np.ndarray] = {}
        self._max_cache_size = 500

    def normalize_vector(self, vector: np.ndarray) -> np.ndarray:
        """Ensure vector is unit normalized (L2 norm = 1)."""
        norm = np.linalg.norm(vector)
        if norm < 1e-8:
            return vector
        return vector / norm

    async def get_image_embedding_cached(
        self, 
        clip: CLIPService, 
        image_url: str, 
        image_bytes: Optional[bytes] = None
    ) -> Optional[np.ndarray]:
        """
        Retrieve cached image embedding or generate a new one via CLIPService.
        """
        if image_url in self._image_cache:
            return self._image_cache[image_url]

        try:
            if not image_bytes and image_url:
                image_bytes = await clip.fetch_image_from_url(image_url)

            if not image_bytes:
                return None

            embedding = await clip.get_image_embedding(image_bytes)
            normalized_emb = self.normalize_vector(embedding)

            # Evict if cache exceeds max size
            if len(self._image_cache) >= self._max_cache_size:
                # Remove oldest item
                first_key = next(iter(self._image_cache))
                del self._image_cache[first_key]

            self._image_cache[image_url] = normalized_emb
            return normalized_emb

        except Exception as e:
            logger.warning(f"Could not generate embedding for image {image_url}: {e}")
            return None

    async def get_text_embedding_cached(
        self, 
        clip: CLIPService, 
        text_prompt: str
    ) -> Optional[np.ndarray]:
        """
        Retrieve cached text embedding or generate via CLIPService.
        """
        if not text_prompt:
            return None

        if text_prompt in self._text_cache:
            return self._text_cache[text_prompt]

        try:
            embedding = await clip.get_text_embedding(text_prompt)
            normalized_emb = self.normalize_vector(embedding)

            if len(self._text_cache) >= self._max_cache_size:
                first_key = next(iter(self._text_cache))
                del self._text_cache[first_key]

            self._text_cache[text_prompt] = normalized_emb
            return normalized_emb

        except Exception as e:
            logger.warning(f"Could not generate text embedding for prompt: {e}")
            return None

embedding_service = EmbeddingService()
