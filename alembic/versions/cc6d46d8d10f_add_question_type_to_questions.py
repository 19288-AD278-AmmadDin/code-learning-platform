"""add_question_type_to_questions

Revision ID: cc6d46d8d10f
Revises: b4b6c6365319
Create Date: 2026-03-02 17:46:50.753165

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'cc6d46d8d10f'
down_revision: Union[str, Sequence[str], None] = 'b4b6c6365319'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add question_type column to questions table."""
    op.add_column(
        'questions',
        sa.Column(
            'question_type',
            sa.String(),
            nullable=False,
            server_default='single_choice'
        )
    )


def downgrade() -> None:
    """Remove question_type column from questions table."""
    op.drop_column('questions', 'question_type')
