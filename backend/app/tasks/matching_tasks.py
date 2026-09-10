"""
Celery Background Tasks for AI Matching
Handles asynchronous CLIP similarity matching and processing status updates.
"""

import logging
import asyncio
from app.tasks.celery_app import celery_app
from app.db.database import SessionLocal
from app.models import Item, AIProcessingStatus
from app.ai.matching_service import matching_service
from app.ai.clip_service import CLIPService

logger = logging.getLogger("findit.tasks.matching")

# Singleton worker-cached CLIP model instance
_worker_clip_model = None

def get_worker_clip():
    global _worker_clip_model
    if _worker_clip_model is None:
        logger.info("Initializing worker-level CLIP model...")
        clip = CLIPService()
        asyncio.run(clip.load_model())
        _worker_clip_model = clip
    return _worker_clip_model

@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def process_item_ai_matching_task(self, item_id: int):
    """
    Celery task to run CLIP similarity matching in the background.
    """
    logger.info(f"Task started: process_item_ai_matching_task for item_id={item_id}")
    db = SessionLocal()
    try:
        item = db.query(Item).filter(Item.id == item_id).first()
        if not item:
            logger.warning(f"Task skipped: Item {item_id} not found.")
            return {"status": "skipped", "reason": "item_not_found"}

        # 1. Update status to PROCESSING
        item.ai_processing_status = AIProcessingStatus.processing
        db.commit()

        # 2. Get worker CLIP model
        clip = get_worker_clip()

        # 3. Run AI matching pipeline
        matches = asyncio.run(
            matching_service.analyze_item_and_find_matches(
                item_id=item_id,
                clip=clip,
                db=db
            )
        )

        # 4. Update status to COMPLETED
        item.ai_processing_status = AIProcessingStatus.completed
        db.commit()

        logger.info(f"Task completed: Item {item_id} processed successfully with {len(matches)} matches.")
        return {"status": "completed", "item_id": item_id, "matches_created": len(matches)}

    except Exception as exc:
        db.rollback()
        logger.error(f"Task error processing item {item_id}: {exc}")
        # Try retrying for transient errors up to max_retries
        try:
            item = db.query(Item).filter(Item.id == item_id).first()
            if item:
                if self.request.retries >= self.max_retries:
                    item.ai_processing_status = AIProcessingStatus.failed
                    db.commit()
                else:
                    self.retry(exc=exc, countdown=5)
        except Exception as retry_exc:
            logger.error(f"Retry attempt failed: {retry_exc}")
        return {"status": "failed", "item_id": item_id, "error": str(exc)}
    finally:
        db.close()
