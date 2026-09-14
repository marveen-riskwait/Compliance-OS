"""customer_note: pinned analysis summary + comment thread per file

Revision ID: c9d3e5a7b1f2
Revises: b7e2d4c1f9a3
Create Date: 2026-09-14 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c9d3e5a7b1f2'
down_revision = 'b7e2d4c1f9a3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'customer_note',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=True),
        sa.Column('kind', sa.String(length=30), nullable=False, server_default='COMMENT'),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], name='fk_customer_note_organization'),
        sa.ForeignKeyConstraint(['customer_id'], ['customer.id'], name='fk_customer_note_customer'),
        sa.ForeignKeyConstraint(['author_id'], ['user.id'], name='fk_customer_note_author'),
        sa.PrimaryKeyConstraint('id', name='pk_customer_note'),
    )
    op.create_index('ix_customer_note_customer', 'customer_note', ['customer_id'])


def downgrade():
    op.drop_index('ix_customer_note_customer', table_name='customer_note')
    op.drop_table('customer_note')
