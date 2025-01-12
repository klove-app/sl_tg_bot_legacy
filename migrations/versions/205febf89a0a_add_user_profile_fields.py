"""add_user_profile_fields

Revision ID: 205febf89a0a
Revises: c525de45ecfe
Create Date: 2025-01-12 17:48:00.290455

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '205febf89a0a'
down_revision: Union[str, None] = 'c525de45ecfe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
