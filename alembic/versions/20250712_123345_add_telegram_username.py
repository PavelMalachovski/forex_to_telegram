"""Add telegram_username field to BotUser

Revision ID: 20250712_123345
Revises: 6982590dd5c9
Create Date: 2025-07-12 12:33:45.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250712_123345'
down_revision = '6982590dd5c9'
branch_labels = None
depends_on = None


def upgrade():
    """Add telegram_username column to bot_users table."""
    op.add_column('bot_users', sa.Column('telegram_username', sa.String(length=100), nullable=True))


def downgrade():
    """Remove telegram_username column from bot_users table."""
    op.drop_column('bot_users', 'telegram_username')
