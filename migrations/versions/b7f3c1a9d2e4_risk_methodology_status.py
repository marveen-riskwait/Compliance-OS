"""risk_methodology status lifecycle (DRAFT/ACTIVE/ARCHIVED)

Revision ID: b7f3c1a9d2e4
Revises: 4079738667dd
Create Date: 2026-07-31 10:20:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b7f3c1a9d2e4'
down_revision = '4079738667dd'
branch_labels = None
depends_on = None


def upgrade():
    # Existing rows are the live methodologies -> ACTIVE. New org drafts start
    # DRAFT (set by the service), so a server_default of ACTIVE is correct for
    # the backfill only.
    with op.batch_alter_table('risk_methodology', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(length=20),
                                      nullable=False, server_default='ACTIVE'))


def downgrade():
    with op.batch_alter_table('risk_methodology', schema=None) as batch_op:
        batch_op.drop_column('status')
