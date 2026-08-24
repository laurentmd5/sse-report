"""Add task confirmation to interventions

Revision ID: a4c7e8f1b2d3
Revises: f09366ff3b17
Create Date: 2026-08-24

"""
from alembic import op
import sqlalchemy as sa


revision = 'a4c7e8f1b2d3'
down_revision = 'd9f8bfab93f9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('interventions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('task_confirmation', sa.String(length=100), nullable=True))


def downgrade():
    with op.batch_alter_table('interventions', schema=None) as batch_op:
        batch_op.drop_column('task_confirmation')