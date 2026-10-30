"""draft design (Story 12.6): the design directions of a static or dynamic draft

Revision ID: f2b8c4d6e1a3
Revises: e7a1d2c3b4f5
Create Date: 2026-10-30 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f2b8c4d6e1a3'
down_revision: Union[str, Sequence[str], None] = 'e7a1d2c3b4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('spec_drafts', sa.Column('design', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('spec_drafts', 'design')
