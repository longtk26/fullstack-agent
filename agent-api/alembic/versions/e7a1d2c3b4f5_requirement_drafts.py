"""requirement drafts (Stories 2.4, 12.4): source vs mode, drafted specs, validation, usage, progress

Revision ID: e7a1d2c3b4f5
Revises: c3d4e5f6a7b8
Create Date: 2026-10-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e7a1d2c3b4f5'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    # `mode` used to hold the input source (requirement | frontend); it now holds the generation mode.
    op.add_column('spec_drafts', sa.Column(
        'source', sqlmodel.sql.sqltypes.AutoString(length=32), server_default='requirement', nullable=False
    ))
    op.execute("UPDATE spec_drafts SET source = mode, mode = 'backend'")
    op.add_column('spec_drafts', sa.Column('requirement_format', sqlmodel.sql.sqltypes.AutoString(length=16), nullable=True))
    op.add_column('spec_drafts', sa.Column('requirement_file_name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True))
    op.add_column('spec_drafts', sa.Column('inputs', _JSONB, server_default='{}', nullable=False))
    op.add_column('spec_drafts', sa.Column('progress', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True))
    op.add_column('spec_drafts', sa.Column('attempts', sa.Integer(), server_default='0', nullable=False))
    # JSON (not JSONB) keeps the drafted specs' key order for the editor.
    op.add_column('spec_drafts', sa.Column('backend_spec', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('spec_drafts', sa.Column('frontend_spec', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('spec_drafts', sa.Column('validation', _JSONB, server_default='{}', nullable=False))
    op.add_column('spec_drafts', sa.Column('usage', _JSONB, server_default='{}', nullable=False))
    op.add_column('spec_drafts', sa.Column('worker_id', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True))
    op.add_column('spec_drafts', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('spec_drafts', sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_spec_drafts_status'), 'spec_drafts', ['status'], unique=False)
    op.create_index(op.f('ix_spec_drafts_created_at'), 'spec_drafts', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_spec_drafts_created_at'), table_name='spec_drafts')
    op.drop_index(op.f('ix_spec_drafts_status'), table_name='spec_drafts')
    for column in (
        'finished_at', 'started_at', 'worker_id', 'usage', 'validation', 'frontend_spec', 'backend_spec',
        'attempts', 'progress', 'inputs', 'requirement_file_name', 'requirement_format',
    ):
        op.drop_column('spec_drafts', column)
    op.execute("UPDATE spec_drafts SET mode = source")
    op.drop_column('spec_drafts', 'source')
