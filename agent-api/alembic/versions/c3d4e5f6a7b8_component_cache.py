"""component cache (Story 17.3): cached custom components

Revision ID: c3d4e5f6a7b8
Revises: a6f75b3fd70b
Create Date: 2026-10-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'a6f75b3fd70b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'component_cache',
        sa.Column('key', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('source_generation_id', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
        sa.Column('engine', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column('model', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
        sa.Column('hits', sa.Integer(), server_default='0', nullable=False),
        sa.Column('saved_seconds', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('key', name=op.f('component_cache_pkey')),
    )
    op.create_index(op.f('ix_component_cache_name'), 'component_cache', ['name'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_component_cache_name'), table_name='component_cache')
    op.drop_table('component_cache')
