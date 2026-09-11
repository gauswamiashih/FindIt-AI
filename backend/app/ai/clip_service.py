"""
CLIP Service – Core AI Matching Engine (Disabled for Free Tier)
"""

import logging
import asyncio
from typing import List, Optional, Union

logger = logging.getLogger("findit.clip")

class CLIPService:
    """
    Stubbed service for environments without PyTorch/OpenCLIP.
    """

    def __init__(self):
        self.model = None
        self.preprocess = None
        self.tokenizer = None
        self.device = "cpu"

    async def load_model(self):
        logger.info("CLIP model disabled for Free Tier.")
        return None

    def build_item_description(
        self,
        title: str,
        category: str = "",
        brand: str = "",
        color: str = "",
        description: str = "",
    ) -> str:
        parts = [f"a {color} {brand} {category}".strip()]
        if title:
            parts.append(title)
        if description:
            parts.append(description[:200])
        return ". ".join(filter(None, parts))

    async def fetch_image_from_url(self, url: str) -> bytes:
        return b""

