from .BaseDataModel import BaseDataModel
from .db_schemes import User
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid


class UserModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client)

    @classmethod
    async def create_instance(cls, db_client):
        instance = cls(db_client=db_client)
        return instance

    async def create_user(self, user: User):
        async with self.db_client() as session:
            async with session.begin():
                session.add(user)
            await session.commit()
            await session.refresh(user)
        return user

    async def get_by_id(self, user_id: str):
        """Fetch a User by UUID primary key. Returns None if not found."""
        async with self.db_client() as session:
            async with session.begin():
                result = await session.execute(
                    select(User).where(User.user_id == uuid.UUID(str(user_id)))
                )
                return result.scalar_one_or_none()

    async def get_by_email(self, email: str):
        """Fetch a User by email address. Returns None if not found."""
        async with self.db_client() as session:
            async with session.begin():
                result = await session.execute(
                    select(User).where(User.email == email)
                )
                return result.scalar_one_or_none()

    async def update_user(self, user: User):
        """Persist changes to an existing User row."""
        async with self.db_client() as session:
            async with session.begin():
                merged = await session.merge(user)
            await session.commit()
            await session.refresh(merged)
        return merged

    async def get_all_users(self, page: int = 1, page_size: int = 20):
        """Admin listing: returns (users_list, total_pages)."""
        async with self.db_client() as session:
            async with session.begin():
                from sqlalchemy import func
                total = (await session.execute(
                    select(func.count(User.user_id))
                )).scalar_one()
                total_pages = total // page_size + (1 if total % page_size else 0)
                result = await session.execute(
                    select(User)
                    .order_by(User.created_at.desc())
                    .limit(page_size)
                    .offset((page - 1) * page_size)
                )
                users = result.scalars().all()
        return users, total_pages
