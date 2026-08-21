from .BaseDataModel import BaseDataModel
from .db_schemes import Asset
from sqlalchemy.future import select



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
                # Check for existing assets with the same name in this project
                query = select(Asset).where(
                    Asset.asset_project_id == asset.asset_project_id,
                    Asset.asset_name == asset.asset_name
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

    async def get_all_project_assets(self, asset_project_id: int, asset_type: str, only_latest: bool = True):
        async with self.db_client() as session:
            query = select(Asset).where(
                Asset.asset_project_id == asset_project_id,
                Asset.asset_type == asset_type
            )
            if only_latest:
                query = query.where(Asset.is_latest == True)
            result = await session.execute(query)
            assets = result.scalars().all()
        return assets

    async def get_asset_record(self, asset_project_id: int, asset_name: str, only_latest: bool = True):
        async with self.db_client() as session:
            query = select(Asset).where(
                Asset.asset_project_id == asset_project_id,
                Asset.asset_name == asset_name
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
                Asset.asset_name == asset_name
            ).order_by(Asset.asset_version.asc())
            result = await session.execute(query)
            return result.scalars().all()