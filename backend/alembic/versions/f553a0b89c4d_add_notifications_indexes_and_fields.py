"""Add notifications indexes and related fields

Revision ID: f553a0b89c4d
Revises: e443b0e78b3d
Create Date: 2026-09-10 22:47:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f553a0b89c4d'
down_revision: Union[str, Sequence[str], None] = 'e443b0e78b3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('notifications', sa.Column('related_item_id', sa.Integer(), nullable=True))
    op.add_column('notifications', sa.Column('related_match_id', sa.Integer(), nullable=True))
    
    # Indexes on notifications
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
    op.create_index(op.f('ix_notifications_is_read'), 'notifications', ['is_read'], unique=False)
    
    # Indexes on matches
    op.create_index(op.f('ix_matches_lost_item_id'), 'matches', ['lost_item_id'], unique=False)
    op.create_index(op.f('ix_matches_found_item_id'), 'matches', ['found_item_id'], unique=False)
    op.create_index(op.f('ix_matches_status'), 'matches', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_matches_status'), table_name='matches')
    op.drop_index(op.f('ix_matches_found_item_id'), table_name='matches')
    op.drop_index(op.f('ix_matches_lost_item_id'), table_name='matches')
    op.drop_index(op.f('ix_notifications_is_read'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_column('notifications', 'related_match_id')
    op.drop_column('notifications', 'related_item_id')
