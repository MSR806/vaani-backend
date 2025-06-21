"""add book type column

Revision ID: add_book_type_column
Revises: 87cd9000dd98
Create Date: 2025-06-21 09:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_book_type_column'
down_revision: Union[str, Sequence[str], None] = '87cd9000dd98'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add type column to books table."""
    # Add the type column with ENUM values and default value
    op.add_column('books', sa.Column('type', sa.Enum('SOURCE', 'REIMAGINED', name='booktype'), nullable=False, server_default='SOURCE'))


def downgrade() -> None:
    """Remove type column from books table."""
    # Drop the type column
    op.drop_column('books', 'type') 