from .BaseDataModel import BaseDataModel
from .db_schemes import ApiKey
from sqlalchemy.future import select
import uuid


class ApiKeyModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client)

    @classmethod
    async def create_instance(cls, db_client):
        instance = cls(db_client=db_client)
        return instance

    async def create_key(self, api_key: ApiKey):
        """Persist a new ApiKey row (hashed_key must already be set)."""
        async with self.db_client() as session:
            async with session.begin():
                session.add(api_key)
            await session.commit()
            await session.refresh(api_key)
        return api_key

    async def get_by_hashed_key(self, hashed_key: str):
        """Look up an active ApiKey by its stored hash. Returns None if not found or revoked."""
        async with self.db_client() as session:
            async with session.begin():
                result = await session.execute(
                    select(ApiKey).where(
                        ApiKey.hashed_key == hashed_key,
                        ApiKey.is_active == True,  # noqa: E712
                        ApiKey.revoked_at == None,  # noqa: E711
                    )
                )
                return result.scalar_one_or_none()

    async def get_keys_for_user(self, user_id: str):
        """Return all non-revoked ApiKey rows for the given user UUID."""
        async with self.db_client() as session:
            async with session.begin():
                result = await session.execute(
                    select(ApiKey).where(
                        ApiKey.user_id == uuid.UUID(str(user_id)),
                        ApiKey.revoked_at == None,  # noqa: E711
                    ).order_by(ApiKey.created_at.desc())
                )
                return result.scalars().all()

    async def revoke_key(self, key_id: str, user_id: str):
        """Soft-revoke a key by setting revoked_at. Returns the updated row or None."""
        from datetime import datetime, timezone
        from sqlalchemy import update
        async with self.db_client() as session:
            async with session.begin():
                await session.execute(
                    update(ApiKey)
                    .where(
                        ApiKey.key_id == uuid.UUID(str(key_id)),
                        ApiKey.user_id == uuid.UUID(str(user_id)),
                    )
                    .values(revoked_at=datetime.now(timezone.utc), is_active=False)
                )
            await session.commit()
