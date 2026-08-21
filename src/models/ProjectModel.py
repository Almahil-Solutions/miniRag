from .BaseDataModel import BaseDataModel
from .db_schemes import Project
from sqlalchemy.future import select
from sqlalchemy import func
import uuid as _uuid


class ProjectModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client)
        self.db_client = self.db_client

    @classmethod
    async def create_instance(cls, db_client):
        instance = cls(db_client)
        return instance

    async def create_project(self, project: Project):
        # try:
            async with self.db_client() as session:
                async with session.begin():
                    session.add(project)
                await session.commit()
                await session.refresh(project)
            return project

        # except Exception as e:
            # return e

    async def get_project_by_id(self, project_id: int, include_deleted: bool = False):
        """Return the Project with *project_id* (integer PK), or None if it does not exist."""
        async with self.db_client() as session:
            async with session.begin():
                query = select(Project).where(Project.project_id == project_id)
                if not include_deleted:
                    query = query.where(Project.deleted_at.is_(None))
                result = await session.execute(query)
                return result.scalar_one_or_none()

    async def get_project_by_uuid(self, project_uuid, include_deleted: bool = False):
        """Return the Project with *project_uuid*, or None if it does not exist."""
        if not isinstance(project_uuid, _uuid.UUID):
            project_uuid = _uuid.UUID(str(project_uuid))
        async with self.db_client() as session:
            async with session.begin():
                query = select(Project).where(Project.project_uuid == project_uuid)
                if not include_deleted:
                    query = query.where(Project.deleted_at.is_(None))
                result = await session.execute(query)
                return result.scalar_one_or_none()

    async def get_project_or_create_one(self, project_id: int):
        async with self.db_client() as session:
            async with session.begin():
                query = select(Project).where(
                    Project.project_id == project_id,
                    Project.deleted_at.is_(None)
                )
                result = await session.execute(query)
                project = result.scalar_one_or_none()

                if project is None:
                    project_record = Project(
                        project_id=project_id
                    )
                    project = await self.create_project(project=project_record)
                return project

    async def get_all_projects(self, page: int = 1, page_size: int = 10, owner_user_id = None):
        async with self.db_client() as session:
            async with session.begin():
                count_query = select(func.count(Project.project_id)).where(Project.deleted_at.is_(None))
                if owner_user_id is not None:
                    count_query = count_query.where(Project.owner_user_id == owner_user_id)

                total_documents = await session.execute(count_query)
                total_documents = total_documents.scalar_one()

                total_pages = total_documents // page_size
                if total_documents % page_size > 0:
                    total_pages += 1

                query = select(Project).where(Project.deleted_at.is_(None))
                if owner_user_id is not None:
                    query = query.where(Project.owner_user_id == owner_user_id)

                query = query.order_by(Project.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
                result = await session.execute(query)
                projects = result.scalars().all()

                return projects, total_pages

    async def soft_delete_project_by_uuid(self, project_uuid) -> bool:
        """Soft delete a project and record deletion timestamp."""
        if not isinstance(project_uuid, _uuid.UUID):
            project_uuid = _uuid.UUID(str(project_uuid))
        async with self.db_client() as session:
            async with session.begin():
                query = select(Project).where(
                    Project.project_uuid == project_uuid,
                    Project.deleted_at.is_(None)
                )
                result = await session.execute(query)
                project = result.scalar_one_or_none()
                if not project:
                    return False
                project.deleted_at = func.now()
                session.add(project)
                await session.commit()
                return True
