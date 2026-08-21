"""add asset_version and is_latest columns to assets table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-21 19:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add asset_version and is_latest columns
    op.add_column(
        'assets',
        sa.Column('asset_version', sa.Integer(), nullable=False, server_default='1')
    )
    op.add_column(
        'assets',
        sa.Column('is_latest', sa.Boolean(), nullable=False, server_default=sa.text('true'))
    )
    op.create_index(
        op.f('ix_assets_is_latest'),
        'assets',
        ['is_latest'],
        unique=False
    )
    op.create_index(
        'ix_asset_project_name_version',
        'assets',
        ['asset_project_id', 'asset_name', 'asset_version'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_asset_project_name_version', table_name='assets')
    op.drop_index(op.f('ix_assets_is_latest'), table_name='assets')
    op.drop_column('assets', 'is_latest')
    op.drop_column('assets', 'asset_version')
