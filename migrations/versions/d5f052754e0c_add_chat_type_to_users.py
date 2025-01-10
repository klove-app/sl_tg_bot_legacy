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
    # SQLite не поддерживает изменение колонок, поэтому:
    # 1. Создаем новую таблицу
    # 2. Копируем данные
    # 3. Удаляем старую таблицу
    # 4. Переименовываем новую таблицу
    
    # Создаем временную таблицу
    op.create_table('users_new',
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('goal_km', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('chat_type', sa.String(), nullable=False, server_default='group'),
        sa.PrimaryKeyConstraint('user_id')
    )
    
    # Копируем данные
    op.execute(
        'INSERT INTO users_new (user_id, username, goal_km, is_active, chat_type) '
        'SELECT user_id, username, goal_km, is_active, "group" FROM users'
    )
    
    # Удаляем старую таблицу
    op.drop_table('users')
    
    # Переименовываем новую таблицу
    op.rename_table('users_new', 'users')


def downgrade():
    # При откате создаем таблицу без chat_type
    op.create_table('users_new',
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('goal_km', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('user_id')
    )
    
    # Копируем данные без chat_type
    op.execute(
        'INSERT INTO users_new (user_id, username, goal_km, is_active) '
        'SELECT user_id, username, goal_km, is_active FROM users'
    )
    
    # Удаляем старую таблицу
    op.drop_table('users')
    
    # Переименовываем новую таблицу
    op.rename_table('users_new', 'users')
