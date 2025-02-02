"""Add chat_id to running_log

Revision ID: add_chat_id_to_running_log
Create Date: 2025-02-02 19:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_chat_id_to_running_log'
down_revision: Union[str, None] = 'add_chat_type_to_running_log'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('running_log', sa.Column('chat_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_running_log_chat_id'), 'running_log', ['chat_id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_running_log_chat_id'), table_name='running_log')
    op.drop_column('running_log', 'chat_id')
    # ### end Alembic commands ### 