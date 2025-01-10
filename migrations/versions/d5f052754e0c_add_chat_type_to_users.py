"""add chat_type to users

Revision ID: d5f052754e0c
Revises: a36ab4c1439b
Create Date: 2024-01-10 15:42:23.123456

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd5f052754e0c'
down_revision = 'a36ab4c1439b'
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем колонку chat_type
    op.execute('ALTER TABLE users ADD COLUMN chat_type VARCHAR DEFAULT "group" NOT NULL')


def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('chat_type')
