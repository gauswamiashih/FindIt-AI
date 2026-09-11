"""
Embedding Service (Disabled for Free Tier)
"""

import logging
from typing import Dict, Optional, List, Tuple

logger = logging.getLogger("findit.ai.embedding")

class EmbeddingService:
    def __init__(self):
        pass

    async def get_image_embedding_cached(
        self, 
        clip: any, 
        image_url: str, 
        image_bytes: Optional[bytes] = None
    ) -> Optional[any]:
        return None

    async def get_text_embedding_cached(
        self, 
        clip: any, 
        text_prompt: str
    ) -> Optional[any]:
        return None

embedding_service = EmbeddingService()

