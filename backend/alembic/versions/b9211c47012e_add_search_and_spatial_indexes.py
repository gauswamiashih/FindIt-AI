"""Add search and spatial indexes

Revision ID: b9211c47012e
Revises: f553a0b89c4d
Create Date: 2026-09-10 22:56:30.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9211c47012e'
down_revision: Union[str, Sequence[str], None] = 'f553a0b89c4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(op.f('ix_items_created_at'), 'items', ['created_at'], unique=False)
    op.create_index('ix_items_lat_lng', 'items', ['location_lat', 'location_lng'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_items_lat_lng', table_name='items')
    op.drop_index(op.f('ix_items_created_at'), table_name='items')
