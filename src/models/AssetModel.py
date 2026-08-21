from .BaseDataModel import BaseDataModel
from .db_schemes import Asset
from sqlalchemy.future import select
from sqlalchemy import func
import uuid as _uuid


class AssetModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client)
        self.db_client = self.db_client

    @classmethod
    async def create_instance(cls, db_client):
        instance = cls(db_client)
        return instance

    async def create_asset(self, asset: Asset):
        async with self.db_client() as session:
            async with session.begin():
                # Check for existing non-deleted assets with the same name in this project
                query = select(Asset).where(
                    Asset.asset_project_id == asset.asset_project_id,
                    Asset.asset_name == asset.asset_name,
                    Asset.deleted_at.is_(None)
                ).order_by(Asset.asset_version.desc())
                result = await session.execute(query)
                existing_assets = result.scalars().all()

                if existing_assets:
                    latest_existing = existing_assets[0]
                    asset.asset_version = (latest_existing.asset_version or 1) + 1
                    for prev_asset in existing_assets:
                        prev_asset.is_latest = False
                else:
                    asset.asset_version = 1

                asset.is_latest = True
                session.add(asset)

            await session.commit()
            await session.refresh(asset)
        return asset

    async def get_all_project_assets(self, asset_project_id: int, asset_type: str = None, only_latest: bool = True):
        async with self.db_client() as session:
            query = select(Asset).where(
                Asset.asset_project_id == asset_project_id,
                Asset.deleted_at.is_(None)
            )
            if asset_type:
                query = query.where(Asset.asset_type == asset_type)
            if only_latest:
                query = query.where(Asset.is_latest == True)
            result = await session.execute(query)
            assets = result.scalars().all()
        return assets

    async def get_project_assets_paginated(
        self,
        asset_project_id: int,
        page: int = 1,
        page_size: int = 10,
        asset_type: str = None,
        only_latest: bool = True
    ):
        async with self.db_client() as session:
            count_query = select(func.count(Asset.asset_id)).where(
                Asset.asset_project_id == asset_project_id,
                Asset.deleted_at.is_(None)
            )
            if asset_type:
                count_query = count_query.where(Asset.asset_type == asset_type)
            if only_latest:
                count_query = count_query.where(Asset.is_latest == True)

            total_records = await session.execute(count_query)
            total_records = total_records.scalar_one()

            total_pages = total_records // page_size
            if total_records % page_size > 0:
                total_pages += 1

            query = select(Asset).where(
                Asset.asset_project_id == asset_project_id,
                Asset.deleted_at.is_(None)
            )
            if asset_type:
                query = query.where(Asset.asset_type == asset_type)
            if only_latest:
                query = query.where(Asset.is_latest == True)

            query = query.order_by(Asset.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
            result = await session.execute(query)
            assets = result.scalars().all()

            return assets, total_pages, total_records

    async def get_asset_by_uuid(self, asset_uuid, asset_project_id: int = None, include_deleted: bool = False):
        if not isinstance(asset_uuid, _uuid.UUID):
            asset_uuid = _uuid.UUID(str(asset_uuid))
        async with self.db_client() as session:
            query = select(Asset).where(Asset.asset_uuid == asset_uuid)
            if asset_project_id is not None:
                query = query.where(Asset.asset_project_id == asset_project_id)
            if not include_deleted:
                query = query.where(Asset.deleted_at.is_(None))
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def get_asset_by_id(self, asset_id: int, asset_project_id: int = None, include_deleted: bool = False):
        async with self.db_client() as session:
            query = select(Asset).where(Asset.asset_id == asset_id)
            if asset_project_id is not None:
                query = query.where(Asset.asset_project_id == asset_project_id)
            if not include_deleted:
                query = query.where(Asset.deleted_at.is_(None))
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def get_asset_record(self, asset_project_id: int, asset_name: str, only_latest: bool = True):
        async with self.db_client() as session:
            query = select(Asset).where(
                Asset.asset_project_id == asset_project_id,
                Asset.asset_name == asset_name,
                Asset.deleted_at.is_(None)
            )
            if only_latest:
                query = query.where(Asset.is_latest == True)
            query = query.order_by(Asset.asset_version.desc())
            result = await session.execute(query)
            asset = result.scalars().first()
        return asset

    async def get_asset_versions(self, asset_project_id: int, asset_name: str):
        async with self.db_client() as session:
            query = select(Asset).where(
                Asset.asset_project_id == asset_project_id,
                Asset.asset_name == asset_name,
                Asset.deleted_at.is_(None)
            ).order_by(Asset.asset_version.asc())
            result = await session.execute(query)
            return result.scalars().all()

    async def soft_delete_asset_by_uuid(self, asset_uuid, asset_project_id: int = None) -> bool:
        """Soft delete an asset and mark as not latest."""
        if not isinstance(asset_uuid, _uuid.UUID):
            asset_uuid = _uuid.UUID(str(asset_uuid))
        async with self.db_client() as session:
            async with session.begin():
                query = select(Asset).where(
                    Asset.asset_uuid == asset_uuid,
                    Asset.deleted_at.is_(None)
                )
                if asset_project_id is not None:
                    query = query.where(Asset.asset_project_id == asset_project_id)
                result = await session.execute(query)
                asset = result.scalar_one_or_none()
                if not asset:
                    return False
                asset.deleted_at = func.now()
                asset.is_latest = False
                session.add(asset)
                await session.commit()
                return True