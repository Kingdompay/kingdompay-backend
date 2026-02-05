"""Add savings_goals table

Revision ID: d4e5f6a78901
Revises: c2f0ca1745c9
Create Date: 2026-01-22 13:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd4e5f6a78901'
down_revision = 'c2f0ca1745c9'
branch_labels = None
depends_on = None


def upgrade():
    # Create savings_goals table
    op.create_table(
        'savings_goals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('target_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('current_amount', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0.00'),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='KES'),
        sa.Column('icon', sa.String(length=50), nullable=True, server_default='savings'),
        sa.Column('deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('savings_goals', schema=None) as batch_op:
        batch_op.create_index('ix_savings_goals_user_id', ['user_id'], unique=False)


def downgrade():
    with op.batch_alter_table('savings_goals', schema=None) as batch_op:
        batch_op.drop_index('ix_savings_goals_user_id')
    op.drop_table('savings_goals')
