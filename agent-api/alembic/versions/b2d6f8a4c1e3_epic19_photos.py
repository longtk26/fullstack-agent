"""epic 19 photos: image_calls table, upload origin and prompt

Revision ID: b2d6f8a4c1e3
Revises: a1c5e9f3b7d2
Create Date: 2026-10-31 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'b2d6f8a4c1e3'
down_revision: Union[str, Sequence[str], None] = 'a1c5e9f3b7d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add origin and prompt to uploads table (Story 19.3)
    op.add_column('uploads', sa.Column('origin', sqlmodel.sql.sqltypes.AutoString(length=16), server_default='user', nullable=False))
    op.add_column('uploads', sa.Column('prompt', sqlmodel.sql.sqltypes.AutoString(), nullable=True))

    # 2. Create image_calls table (Story 19.2)
    op.create_table(
        'image_calls',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('generation_id', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=True),
        sa.Column('draft_id', sa.Uuid(), nullable=True),
        sa.Column('node_run_id', sa.Uuid(), nullable=True),
        sa.Column('asset_id', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('model', sqlmodel.sql.sqltypes.AutoString(length=128), nullable=False),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(length=16), nullable=False),
        sa.Column('duration_ms', sa.Integer(), server_default='0', nullable=False),
        sa.Column('cost_usd', sa.Float(), nullable=True),
        sa.Column('error', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['generation_id'], ['generations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['draft_id'], ['spec_drafts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['node_run_id'], ['node_runs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_image_calls_generation_id'), 'image_calls', ['generation_id'], unique=False)
    op.create_index(op.f('ix_image_calls_draft_id'), 'image_calls', ['draft_id'], unique=False)
    op.create_index(op.f('ix_image_calls_created_at'), 'image_calls', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_image_calls_created_at'), table_name='image_calls')
    op.drop_index(op.f('ix_image_calls_draft_id'), table_name='image_calls')
    op.drop_index(op.f('ix_image_calls_generation_id'), table_name='image_calls')
    op.drop_table('image_calls')
    op.drop_column('uploads', 'prompt')
    op.drop_column('uploads', 'origin')
