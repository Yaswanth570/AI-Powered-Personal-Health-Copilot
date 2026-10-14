"""create_users_table_and_patient_user_id

Revision ID: 4d2643157691
Revises: 2b38c4d5e6f7
Create Date: 2026-10-14 21:22:35.568680

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d2643157691'
down_revision: Union[str, Sequence[str], None] = '2b38c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema idempotently."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    # 1. Create users table if not already present
    if 'users' not in tables:
        op.create_table(
            'users',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('email', sa.String(length=255), nullable=False),
            sa.Column('hashed_password', sa.String(length=255), nullable=False),
            sa.Column('full_name', sa.String(length=255), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. Add user_id column to patients table if not already present
    patient_columns = [c['name'] for c in inspector.get_columns('patients')]
    if 'user_id' not in patient_columns:
        with op.batch_alter_table('patients', schema=None) as batch_op:
            batch_op.add_column(sa.Column('user_id', sa.String(length=36), nullable=True))
            batch_op.create_index(batch_op.f('ix_patients_user_id'), ['user_id'], unique=False)
            batch_op.create_foreign_key('fk_patients_user_id_users', 'users', ['user_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'patients' in tables:
        patient_columns = [c['name'] for c in inspector.get_columns('patients')]
        if 'user_id' in patient_columns:
            with op.batch_alter_table('patients', schema=None) as batch_op:
                batch_op.drop_constraint('fk_patients_user_id_users', type_='foreignkey')
                batch_op.drop_index(batch_op.f('ix_patients_user_id'))
                batch_op.drop_column('user_id')

    if 'users' in tables:
        op.drop_index(op.f('ix_users_email'), table_name='users')
        op.drop_table('users')
