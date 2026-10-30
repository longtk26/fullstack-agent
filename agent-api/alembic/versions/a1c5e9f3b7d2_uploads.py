"""uploads (Story 15.4): users' images for generated sites

Revision ID: a1c5e9f3b7d2
Revises: f2b8c4d6e1a3
Create Date: 2026-10-30 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'a1c5e9f3b7d2'
down_revision: Union[str, Sequence[str], None] = 'f2b8c4d6e1a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'uploads',
        sa.Column('id', sqlmodel.sql.sqltypes.AutoString(length=40), nullable=False),
        sa.Column('owner_id', sa.Uuid(), nullable=False),
        sa.Column('filename', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('mime', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('bytes', sa.Integer(), nullable=False),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('sha256', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('owner_id', 'sha256', name='uq_uploads_owner_sha256'),
    )
    op.create_index(op.f('ix_uploads_owner_id'), 'uploads', ['owner_id'], unique=False)
    op.create_index(op.f('ix_uploads_created_at'), 'uploads', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_uploads_created_at'), table_name='uploads')
    op.drop_index(op.f('ix_uploads_owner_id'), table_name='uploads')
    op.drop_table('uploads')
