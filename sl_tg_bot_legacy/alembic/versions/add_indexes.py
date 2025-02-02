"""add indexes to running_log table

Revision ID: 2024_add_indexes
Revises: 
Create Date: 2024-02-02 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2024_add_indexes'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Добавляем индексы безопасным способом
    op.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON running_log (user_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_date_added ON running_log (date_added)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_chat_id ON running_log (chat_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_chat_type ON running_log (chat_type)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_user_date ON running_log (user_id, date_added)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_chat_date ON running_log (chat_id, date_added)')

def downgrade():
    # Удаляем индексы в случае отката
    op.execute('DROP INDEX IF EXISTS idx_user_id')
    op.execute('DROP INDEX IF EXISTS idx_date_added')
    op.execute('DROP INDEX IF EXISTS idx_chat_id')
    op.execute('DROP INDEX IF EXISTS idx_chat_type')
    op.execute('DROP INDEX IF EXISTS idx_user_date')
    op.execute('DROP INDEX IF EXISTS idx_chat_date') 