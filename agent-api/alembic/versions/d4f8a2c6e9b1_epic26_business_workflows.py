"""epic 26: business workflows on drafts (spec_drafts.business) and evaluation runs

Revision ID: d4f8a2c6e9b1
Revises: c3e7f9a1b5d4
Create Date: 2026-11-07 06:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd4f8a2c6e9b1'
down_revision: Union[str, Sequence[str], None] = 'c3e7f9a1b5d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Stories 26.1-26.3: the business, the frozen expectations, the binding and the tour of a draft
    op.add_column('spec_drafts', sa.Column('business', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    # Story 26.5: one row per evaluation of a generation (information only, never the generation's status)
    op.create_table(
        'evaluation_runs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('generation_id', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(length=16), nullable=False),
        sa.Column('trigger', sqlmodel.sql.sqltypes.AutoString(length=16), nullable=False),
        sa.Column('provider', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=True),
        sa.Column('expectations_from', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=True),
        sa.Column('score', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('report', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('usage', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('progress', sqlmodel.sql.sqltypes.AutoString(length=128), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['generation_id'], ['generations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_evaluation_runs_generation_id', 'evaluation_runs', ['generation_id'])


def downgrade() -> None:
    op.drop_index('ix_evaluation_runs_generation_id', table_name='evaluation_runs')
    op.drop_table('evaluation_runs')
    op.drop_column('spec_drafts', 'business')
