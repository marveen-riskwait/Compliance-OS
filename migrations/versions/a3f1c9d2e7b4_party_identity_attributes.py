"""party identity attributes: party.nationalities (JSON list), party.gender

Revision ID: a3f1c9d2e7b4
Revises: a1c2e3f4b5d6
Create Date: 2026-09-14 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a3f1c9d2e7b4'
down_revision = 'a1c2e3f4b5d6'
branch_labels = None
depends_on = None


def upgrade():
    # Both nullable: existing persons keep their single `nationality`;
    # serialize() falls back to it when the list is empty.
    with op.batch_alter_table('party', schema=None) as batch_op:
        batch_op.add_column(sa.Column('nationalities', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('gender', sa.String(length=20), nullable=True))


def downgrade():
    with op.batch_alter_table('party', schema=None) as batch_op:
        batch_op.drop_column('gender')
        batch_op.drop_column('nationalities')
