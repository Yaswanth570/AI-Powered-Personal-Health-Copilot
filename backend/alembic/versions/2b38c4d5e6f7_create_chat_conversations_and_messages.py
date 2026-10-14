"""create_chat_conversations_and_messages

Revision ID: 2b38c4d5e6f7
Revises: 15d289c3bebc
Create Date: 2026-10-14 19:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b38c4d5e6f7'
down_revision: Union[str, Sequence[str], None] = '15d289c3bebc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to include chat conversations and message tables."""
    op.create_table(
        'chat_conversations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('patient_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_chat_conversations_patient_id'),
        'chat_conversations',
        ['patient_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_chat_conversations_created_at'),
        'chat_conversations',
        ['created_at'],
        unique=False,
    )
    op.create_index(
        op.f('ix_chat_conversations_updated_at'),
        'chat_conversations',
        ['updated_at'],
        unique=False,
    )

    op.create_table(
        'chat_messages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('conversation_id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('citations', sa.JSON(), nullable=True),
        sa.Column('model_used', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['chat_conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_chat_messages_conversation_id'),
        'chat_messages',
        ['conversation_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_chat_messages_created_at'),
        'chat_messages',
        ['created_at'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_chat_messages_created_at'), table_name='chat_messages')
    op.drop_index(op.f('ix_chat_messages_conversation_id'), table_name='chat_messages')
    op.drop_table('chat_messages')
    op.drop_index(op.f('ix_chat_conversations_updated_at'), table_name='chat_conversations')
    op.drop_index(op.f('ix_chat_conversations_created_at'), table_name='chat_conversations')
    op.drop_index(op.f('ix_chat_conversations_patient_id'), table_name='chat_conversations')
    op.drop_table('chat_conversations')
