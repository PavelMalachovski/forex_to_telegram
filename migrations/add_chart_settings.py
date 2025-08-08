"""Add chart generation settings to users table."""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_chart_settings'
down_revision = 'add_notification_fields'
branch_labels = None
depends_on = None


def upgrade():
    """Add chart generation settings to users table."""
    # Add chart generation settings
    op.add_column('users', sa.Column('charts_enabled', sa.Boolean(), nullable=True, default=False))
    op.add_column('users', sa.Column('chart_type', sa.String(20), nullable=True, default='single'))
    op.add_column('users', sa.Column('chart_window_hours', sa.Integer(), nullable=True, default=2))

    # Add comment to explain the new columns
    op.execute("""
        COMMENT ON COLUMN users.charts_enabled IS 'Whether to include charts with notifications';
        COMMENT ON COLUMN users.chart_type IS 'Type of chart to generate: single, multi, or none';
        COMMENT ON COLUMN users.chart_window_hours IS 'Hours before/after event to include in chart';
    """)


def downgrade():
    """Remove chart generation settings from users table."""
    op.drop_column('users', 'charts_enabled')
    op.drop_column('users', 'chart_type')
    op.drop_column('users', 'chart_window_hours')
