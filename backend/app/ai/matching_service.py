"""
Matching Service
Handles candidate selection, CLIP embedding generation, similarity ranking,
database persistence of Match records, duplicate match prevention, and event notification hooks.
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models import Item, Match, MatchStatus, ItemType, ItemStatus, Notification, NotificationType
from app.ai.clip_service import CLIPService
from app.ai.embedding_service import embedding_service
from app.ai.similarity_service import similarity_service
from app.core.config import settings

logger = logging.getLogger("findit.ai.matching")

class MatchingService:
    def __init__(self, threshold: float = settings.SIMILARITY_THRESHOLD):
        self.threshold = threshold

    async def analyze_item_and_find_matches(
        self,
        item_id: int,
        clip: CLIPService,
        db: Session,
        threshold: Optional[float] = None
    ) -> List[Match]:
        """
        Main AI matching pipeline for a given item:
        1. Fetch source item from DB.
        2. Query active candidates of opposite type.
        3. Extract embeddings and calculate similarity.
        4. Persist Match records above threshold in DB (preventing duplicates).
        5. Trigger notification event hooks.
        """
        logger.info(f"Skipping AI matching for item {item_id}: ML features disabled for Free Tier.")
        return []

        # Extract source item embeddings
        source_image_embs = []
        if source_item.images:
            for img_info in source_item.images[:3]:
                url = img_info.get("url") if isinstance(img_info, dict) else None
                if url:
                    emb = await embedding_service.get_image_embedding_cached(clip, url)
                    if emb is not None:
                        source_image_embs.append(emb)

        source_text_prompt = clip.build_item_description(
            title=source_item.title,
            category=source_item.category or "",
            brand=source_item.brand or "",
            color=source_item.color or "",
            description=source_item.description or ""
        )
        source_text_emb = await embedding_service.get_text_embedding_cached(clip, source_text_prompt)

        new_matches: List[Match] = []

        for candidate in candidates:
            # Determine lost vs found item IDs
            lost_id = source_item.id if source_item.item_type == ItemType.lost else candidate.id
            found_id = candidate.id if source_item.item_type == ItemType.lost else source_item.id

            # Check if match record already exists in DB
            existing_match = db.query(Match).filter(
                Match.lost_item_id == lost_id,
                Match.found_item_id == found_id
            ).first()

            if existing_match:
                continue

            # Candidate image embeddings
            candidate_image_embs = []
            if candidate.images:
                for img_info in candidate.images[:3]:
                    url = img_info.get("url") if isinstance(img_info, dict) else None
                    if url:
                        emb = await embedding_service.get_image_embedding_cached(clip, url)
                        if emb is not None:
                            candidate_image_embs.append(emb)

            # Candidate text embedding
            candidate_text_prompt = clip.build_item_description(
                title=candidate.title,
                category=candidate.category or "",
                brand=candidate.brand or "",
                color=candidate.color or "",
                description=candidate.description or ""
            )
            candidate_text_emb = await embedding_service.get_text_embedding_cached(clip, candidate_text_prompt)

            # Calculate image similarity
            max_img_score = 0.0
            if source_image_embs and candidate_image_embs:
                img_scores = [
                    similarity_service.cosine_similarity(s_emb, c_emb)
                    for s_emb in source_image_embs
                    for c_emb in candidate_image_embs
                ]
                max_img_score = max(img_scores) if img_scores else 0.0

            # Calculate text similarity
            txt_score = 0.0
            if source_text_emb is not None and candidate_text_emb is not None:
                txt_score = similarity_service.cosine_similarity(source_text_emb, candidate_text_emb)

            # Combined score
            combined = similarity_service.compute_combined_score(max_img_score, txt_score)

            if similarity_service.is_match(combined, threshold=match_thresh):
                match_record = Match(
                    lost_item_id=lost_id,
                    found_item_id=found_id,
                    score=combined,
                    image_score=max_img_score,
                    text_score=txt_score,
                    status=MatchStatus.pending
                )
                db.add(match_record)
                db.commit()
                db.refresh(match_record)

                # Trigger notification event hook
                self.trigger_match_notification_hook(match_record, source_item, candidate, db)
                new_matches.append(match_record)

        logger.info(f"✅ AI Matching completed for item {item_id}: {len(new_matches)} matches created.")
        return new_matches

    def trigger_match_notification_hook(
        self,
        match: Match,
        item1: Item,
        item2: Item,
        db: Session
    ):
        """
        Event hook called when a new match is generated above threshold.
        Creates notification records for item reporters via NotificationService.
        """
        try:
            from app.services.notification_service import notification_service
            lost_item = item1 if item1.item_type == ItemType.lost else item2
            found_item = item2 if item1.item_type == ItemType.lost else item1
            notification_service.notify_match(db, match, lost_item, found_item)
        except Exception as e:
            logger.warning(f"Notification hook error: {e}")

matching_service = MatchingService()
