"""add soft delete and cascade foreign keys

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-21 20:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add deleted_at columns
    op.add_column('projects', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_projects_deleted_at'), 'projects', ['deleted_at'], unique=False)

    op.add_column('assets', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_assets_deleted_at'), 'assets', ['deleted_at'], unique=False)

    op.add_column('chunks', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_chunks_deleted_at'), 'chunks', ['deleted_at'], unique=False)

    # Update foreign keys with ON DELETE CASCADE
    # assets -> projects
    try:
        op.drop_constraint('assets_asset_project_id_fkey', 'assets', type_='foreignkey')
    except Exception:
        pass
    op.create_foreign_key(
        'assets_asset_project_id_fkey',
        'assets', 'projects',
        ['asset_project_id'], ['project_id'],
        ondelete='CASCADE'
    )

    # chunks -> projects
    try:
        op.drop_constraint('chunks_chunk_project_id_fkey', 'chunks', type_='foreignkey')
    except Exception:
        pass
    op.create_foreign_key(
        'chunks_chunk_project_id_fkey',
        'chunks', 'projects',
        ['chunk_project_id'], ['project_id'],
        ondelete='CASCADE'
    )

    # chunks -> assets
    try:
        op.drop_constraint('chunks_chunk_asset_id_fkey', 'chunks', type_='foreignkey')
    except Exception:
        pass
    op.create_foreign_key(
        'chunks_chunk_asset_id_fkey',
        'chunks', 'assets',
        ['chunk_asset_id'], ['asset_id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # Revert foreign keys
    op.drop_constraint('chunks_chunk_asset_id_fkey', 'chunks', type_='foreignkey')
    op.create_foreign_key(
        'chunks_chunk_asset_id_fkey',
        'chunks', 'assets',
        ['chunk_asset_id'], ['asset_id']
    )

    op.drop_constraint('chunks_chunk_project_id_fkey', 'chunks', type_='foreignkey')
    op.create_foreign_key(
        'chunks_chunk_project_id_fkey',
        'chunks', 'projects',
        ['chunk_project_id'], ['project_id']
    )

    op.drop_constraint('assets_asset_project_id_fkey', 'assets', type_='foreignkey')
    op.create_foreign_key(
        'assets_asset_project_id_fkey',
        'assets', 'projects',
        ['asset_project_id'], ['project_id']
    )

    # Drop deleted_at columns & indexes
    op.drop_index(op.f('ix_chunks_deleted_at'), table_name='chunks')
    op.drop_column('chunks', 'deleted_at')

    op.drop_index(op.f('ix_assets_deleted_at'), table_name='assets')
    op.drop_column('assets', 'deleted_at')

    op.drop_index(op.f('ix_projects_deleted_at'), table_name='projects')
    op.drop_column('projects', 'deleted_at')
