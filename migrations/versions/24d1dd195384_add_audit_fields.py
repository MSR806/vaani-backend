"""add audit fields

Revision ID: 24d1dd195384
Revises: 
Create Date: 2024-03-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import time

# revision identifiers, used by Alembic.
revision: str = '24d1dd195384'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Get current timestamp
    current_time = int(time.time())
    default_user = 'system'  # Default user for existing records

    # Add columns to books table
    op.add_column('books', sa.Column('created_at', sa.BigInteger(), nullable=True))
    op.add_column('books', sa.Column('updated_at', sa.BigInteger(), nullable=True))
    op.add_column('books', sa.Column('created_by', sa.String(), nullable=True))
    op.add_column('books', sa.Column('updated_by', sa.String(), nullable=True))
    
    # Update existing records
    op.execute(f"UPDATE books SET created_at = {current_time}, updated_at = {current_time}, created_by = '{default_user}', updated_by = '{default_user}'")
    
    # Make columns not nullable
    op.alter_column('books', 'created_at', nullable=False)
    op.alter_column('books', 'updated_at', nullable=False)
    op.alter_column('books', 'created_by', nullable=False)
    op.alter_column('books', 'updated_by', nullable=False)

    # Add columns to chapters table
    op.add_column('chapters', sa.Column('created_at', sa.BigInteger(), nullable=True))
    op.add_column('chapters', sa.Column('updated_at', sa.BigInteger(), nullable=True))
    op.add_column('chapters', sa.Column('created_by', sa.String(), nullable=True))
    op.add_column('chapters', sa.Column('updated_by', sa.String(), nullable=True))
    
    # Update existing records
    op.execute(f"UPDATE chapters SET created_at = {current_time}, updated_at = {current_time}, created_by = '{default_user}', updated_by = '{default_user}'")
    
    # Make columns not nullable
    op.alter_column('chapters', 'created_at', nullable=False)
    op.alter_column('chapters', 'updated_at', nullable=False)
    op.alter_column('chapters', 'created_by', nullable=False)
    op.alter_column('chapters', 'updated_by', nullable=False)

    # Add columns to characters table
    op.add_column('characters', sa.Column('created_at', sa.BigInteger(), nullable=True))
    op.add_column('characters', sa.Column('updated_at', sa.BigInteger(), nullable=True))
    op.add_column('characters', sa.Column('created_by', sa.String(), nullable=True))
    op.add_column('characters', sa.Column('updated_by', sa.String(), nullable=True))
    
    # Update existing records
    op.execute(f"UPDATE characters SET created_at = {current_time}, updated_at = {current_time}, created_by = '{default_user}', updated_by = '{default_user}'")
    
    # Make columns not nullable
    op.alter_column('characters', 'created_at', nullable=False)
    op.alter_column('characters', 'updated_at', nullable=False)
    op.alter_column('characters', 'created_by', nullable=False)
    op.alter_column('characters', 'updated_by', nullable=False)

    # Add columns to images table
    op.add_column('images', sa.Column('created_at', sa.BigInteger(), nullable=True))
    op.add_column('images', sa.Column('updated_at', sa.BigInteger(), nullable=True))
    op.add_column('images', sa.Column('created_by', sa.String(), nullable=True))
    op.add_column('images', sa.Column('updated_by', sa.String(), nullable=True))
    
    # Update existing records
    op.execute(f"UPDATE images SET created_at = {current_time}, updated_at = {current_time}, created_by = '{default_user}', updated_by = '{default_user}'")
    
    # Make columns not nullable
    op.alter_column('images', 'created_at', nullable=False)
    op.alter_column('images', 'updated_at', nullable=False)
    op.alter_column('images', 'created_by', nullable=False)
    op.alter_column('images', 'updated_by', nullable=False)

    # Add columns to scenes table
    op.add_column('scenes', sa.Column('created_at', sa.BigInteger(), nullable=True))
    op.add_column('scenes', sa.Column('updated_at', sa.BigInteger(), nullable=True))
    op.add_column('scenes', sa.Column('created_by', sa.String(), nullable=True))
    op.add_column('scenes', sa.Column('updated_by', sa.String(), nullable=True))
    
    # Update existing records
    op.execute(f"UPDATE scenes SET created_at = {current_time}, updated_at = {current_time}, created_by = '{default_user}', updated_by = '{default_user}'")
    
    # Make columns not nullable
    op.alter_column('scenes', 'created_at', nullable=False)
    op.alter_column('scenes', 'updated_at', nullable=False)
    op.alter_column('scenes', 'created_by', nullable=False)
    op.alter_column('scenes', 'updated_by', nullable=False)

    # Add columns to settings table
    op.add_column('settings', sa.Column('created_at', sa.BigInteger(), nullable=True))
    op.add_column('settings', sa.Column('updated_at', sa.BigInteger(), nullable=True))
    op.add_column('settings', sa.Column('created_by', sa.String(), nullable=True))
    op.add_column('settings', sa.Column('updated_by', sa.String(), nullable=True))
    
    # Update existing records
    op.execute(f"UPDATE settings SET created_at = {current_time}, updated_at = {current_time}, created_by = '{default_user}', updated_by = '{default_user}'")
    
    # Make columns not nullable
    op.alter_column('settings', 'created_at', nullable=False)
    op.alter_column('settings', 'updated_at', nullable=False)
    op.alter_column('settings', 'created_by', nullable=False)
    op.alter_column('settings', 'updated_by', nullable=False)

def downgrade() -> None:
    # Drop columns from all tables
    op.drop_column('settings', 'updated_by')
    op.drop_column('settings', 'created_by')
    op.drop_column('settings', 'updated_at')
    op.drop_column('settings', 'created_at')
    
    op.drop_column('scenes', 'updated_by')
    op.drop_column('scenes', 'created_by')
    op.drop_column('scenes', 'updated_at')
    op.drop_column('scenes', 'created_at')
    
    op.drop_column('images', 'updated_by')
    op.drop_column('images', 'created_by')
    op.drop_column('images', 'updated_at')
    op.drop_column('images', 'created_at')
    
    op.drop_column('characters', 'updated_by')
    op.drop_column('characters', 'created_by')
    op.drop_column('characters', 'updated_at')
    op.drop_column('characters', 'created_at')
    
    op.drop_column('chapters', 'updated_by')
    op.drop_column('chapters', 'created_by')
    op.drop_column('chapters', 'updated_at')
    op.drop_column('chapters', 'created_at')
    
    op.drop_column('books', 'updated_by')
    op.drop_column('books', 'created_by')
    op.drop_column('books', 'updated_at')
    op.drop_column('books', 'created_at')
