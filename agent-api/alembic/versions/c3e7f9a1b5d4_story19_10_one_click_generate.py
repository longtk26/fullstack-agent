"""story 19.10: one-click generate (statuses DRAFTING, NEEDS_REVIEW; spec_drafts.generation_id)

Revision ID: c3e7f9a1b5d4
Revises: b2d6f8a4c1e3
Create Date: 2026-10-31 17:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'c3e7f9a1b5d4'
down_revision: Union[str, Sequence[str], None] = 'b2d6f8a4c1e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add generation_id to spec_drafts table
    op.add_column(
        'spec_drafts',
        sa.Column('generation_id', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=True),
    )
    op.create_index(op.f('ix_spec_drafts_generation_id'), 'spec_drafts', ['generation_id'], unique=False)
    op.create_foreign_key(
        'fk_spec_drafts_generation_id',
        'spec_drafts',
        'generations',
        ['generation_id'],
        ['id'],
        ondelete='SET NULL',
    )

    # 2. Add DRAFTING and NEEDS_REVIEW to generation_status enum
    op.execute("ALTER TYPE generation_status ADD VALUE IF NOT EXISTS 'DRAFTING' BEFORE 'PENDING'")
    op.execute("ALTER TYPE generation_status ADD VALUE IF NOT EXISTS 'NEEDS_REVIEW' AFTER 'REPAIRING'")


def downgrade() -> None:
    # 1. Downgrade generation_status enum
    op.execute("UPDATE generations SET status = 'FAILED' WHERE status IN ('DRAFTING', 'NEEDS_REVIEW')")
    op.execute("ALTER TYPE generation_status RENAME TO generation_status_v_epic19")
    sa.Enum(
        'PENDING',
        'RUNNING',
        'VALIDATING',
        'REPAIRING',
        'COMPLETED',
        'COMPLETED_WITH_WARNINGS',
        'FAILED',
        'CANCELLED',
        name='generation_status',
    ).create(op.get_bind())
    op.execute("ALTER TABLE generations ALTER COLUMN status TYPE generation_status USING status::text::generation_status")
    op.execute("DROP TYPE generation_status_v_epic19")

    # 2. Drop generation_id from spec_drafts
    op.drop_constraint('fk_spec_drafts_generation_id', 'spec_drafts', type_='foreignkey')
    op.drop_index(op.f('ix_spec_drafts_generation_id'), table_name='spec_drafts')
    op.drop_column('spec_drafts', 'generation_id')
