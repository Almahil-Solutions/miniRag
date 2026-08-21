from .BaseDataModel import BaseDataModel
from .db_schemes import DataChunk
from sqlalchemy.future import select
from sqlalchemy import delete, func


class ChunkModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client)
        self.db_client = self.db_client

    @classmethod
    async def create_instance(cls,db_client):
        instance = cls(db_client)
        return instance


    async def create_chunk(self, chunk: DataChunk):
        async with self.db_client() as session:
            async with session.begin():
                session.add(chunk)
                await session.commit()
                await session.refresh(chunk)
            return chunk

    async def get_chunk(self, chunk_id: int, include_deleted: bool = False):
        async with self.db_client() as session:
            query = select(DataChunk).where(DataChunk.chunk_id == chunk_id)
            if not include_deleted:
                query = query.where(DataChunk.deleted_at.is_(None))
            result = await session.execute(query)
            chunk = result.scalar_one_or_none()
            return chunk

    async def insert_many_chunks(self, chunks: list, batch_size: int = 100):
        async with self.db_client() as session:
            async with session.begin():
                for i in range(0, len(chunks), batch_size):
                    batch = chunks[i:i+batch_size]
                    session.add_all(batch)
                await session.commit()                
        return len(chunks)

    async def delete_chunks_by_project_id(self, project_id: int):
        async with self.db_client() as session:
            query = delete(DataChunk).where(DataChunk.chunk_project_id == project_id)
            result = await session.execute(query)
            await session.commit()
        return result.rowcount

    async def soft_delete_chunks_by_project_id(self, project_id: int):
        async with self.db_client() as session:
            from sqlalchemy import update
            query = (
                update(DataChunk)
                .where(
                    DataChunk.chunk_project_id == project_id,
                    DataChunk.deleted_at.is_(None)
                )
                .values(deleted_at=func.now())
            )
            result = await session.execute(query)
            await session.commit()
            return result.rowcount

    async def soft_delete_chunks_by_asset_id(self, asset_id: int):
        async with self.db_client() as session:
            from sqlalchemy import update
            query = (
                update(DataChunk)
                .where(
                    DataChunk.chunk_asset_id == asset_id,
                    DataChunk.deleted_at.is_(None)
                )
                .values(deleted_at=func.now())
            )
            result = await session.execute(query)
            await session.commit()
            return result.rowcount

    async def get_project_chunks(self, project_id: int, page_num: int = 1, page_size: int = 50):
        async with self.db_client() as session:
            query = (
                select(DataChunk)
                .where(
                    DataChunk.chunk_project_id == project_id,
                    DataChunk.deleted_at.is_(None)
                )
                .limit(page_size)
                .offset((page_num - 1) * page_size)
            )
            result = await session.execute(query)
            records = result.scalars().all()
        return records

    async def get_chunks_by_asset_id(self, asset_id: int, page_num: int = 1, page_size: int = 50):
        async with self.db_client() as session:
            query = (
                select(DataChunk)
                .where(
                    DataChunk.chunk_asset_id == asset_id,
                    DataChunk.deleted_at.is_(None)
                )
                .order_by(DataChunk.chunk_order.asc())
                .limit(page_size)
                .offset((page_num - 1) * page_size)
            )
            result = await session.execute(query)
            return result.scalars().all()

    async def count_project_chunks(self, project_id: int):
        records_count = 0
        async with self.db_client() as session:
            query = select(func.count(DataChunk.chunk_id)).where(
                DataChunk.chunk_project_id == project_id,
                DataChunk.deleted_at.is_(None)
            )
            result = await session.execute(query)
            records_count = result.scalar_one_or_none()
        return records_count

    async def count_asset_chunks(self, asset_id: int):
        records_count = 0
        async with self.db_client() as session:
            query = select(func.count(DataChunk.chunk_id)).where(
                DataChunk.chunk_asset_id == asset_id,
                DataChunk.deleted_at.is_(None)
            )
            result = await session.execute(query)
            records_count = result.scalar_one_or_none()
        return records_count
