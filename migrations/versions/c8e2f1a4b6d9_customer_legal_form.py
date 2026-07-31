"""customer legal_form + requirement_definition applies_legal_form

Revision ID: c8e2f1a4b6d9
Revises: b7f3c1a9d2e4
Create Date: 2026-07-31 12:05:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c8e2f1a4b6d9'
down_revision = 'b7f3c1a9d2e4'
branch_labels = None
depends_on = None


def upgrade():
    # Both nullable — existing customers have no sub-type (NULL) and existing
    # requirements apply to every legal form (NULL), so no backfill is needed.
    with op.batch_alter_table('customer', schema=None) as batch_op:
        batch_op.add_column(sa.Column('legal_form', sa.String(length=30), nullable=True))
    with op.batch_alter_table('requirement_definition', schema=None) as batch_op:
        batch_op.add_column(sa.Column('applies_legal_form', sa.String(length=120), nullable=True))


def downgrade():
    with op.batch_alter_table('requirement_definition', schema=None) as batch_op:
        batch_op.drop_column('applies_legal_form')
    with op.batch_alter_table('customer', schema=None) as batch_op:
        batch_op.drop_column('legal_form')
