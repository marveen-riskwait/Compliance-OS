"""per-party documents: document.party_id, requirement_instance.party_id,
requirement_definition.per_party

Revision ID: d4a7e9c2f1b8
Revises: c8e2f1a4b6d9
Create Date: 2026-07-31 14:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd4a7e9c2f1b8'
down_revision = 'c8e2f1a4b6d9'
branch_labels = None
depends_on = None


def upgrade():
    # party_id columns are nullable (existing rows are customer-level, party-less).
    # per_party defaults to false for existing definitions (server_default '0').
    with op.batch_alter_table('document', schema=None) as batch_op:
        batch_op.add_column(sa.Column('party_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_document_party', 'party', ['party_id'], ['id'])
    with op.batch_alter_table('requirement_instance', schema=None) as batch_op:
        batch_op.add_column(sa.Column('party_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_requirement_instance_party', 'party', ['party_id'], ['id'])
    with op.batch_alter_table('requirement_definition', schema=None) as batch_op:
        batch_op.add_column(sa.Column('per_party', sa.Boolean(), nullable=False,
                                      server_default=sa.false()))


def downgrade():
    with op.batch_alter_table('requirement_definition', schema=None) as batch_op:
        batch_op.drop_column('per_party')
    with op.batch_alter_table('requirement_instance', schema=None) as batch_op:
        batch_op.drop_constraint('fk_requirement_instance_party', type_='foreignkey')
        batch_op.drop_column('party_id')
    with op.batch_alter_table('document', schema=None) as batch_op:
        batch_op.drop_constraint('fk_document_party', type_='foreignkey')
        batch_op.drop_column('party_id')
