"""address.label — a free label to tell several addresses apart

Revision ID: b7e2d4c1f9a3
Revises: a3f1c9d2e7b4
Create Date: 2026-09-14 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b7e2d4c1f9a3'
down_revision = 'a3f1c9d2e7b4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('address', schema=None) as batch_op:
        batch_op.add_column(sa.Column('label', sa.String(length=80), nullable=True))


def downgrade():
    with op.batch_alter_table('address', schema=None) as batch_op:
        batch_op.drop_column('label')
