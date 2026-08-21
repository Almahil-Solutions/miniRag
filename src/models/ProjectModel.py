from .BaseDataModel import BaseDataModel
from .db_schemes import Project
from sqlalchemy.future import select
from sqlalchemy import func


class ProjectModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client)
        self.db_client = self.db_client

    @classmethod
    async def create_instance(cls,db_client):
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
    
    async def get_project_by_id(self, project_id: int):
        """Return the Project with *project_id*, or None if it does not exist.

        Unlike ``get_project_or_create_one`` this method is a pure read: it
        never auto-creates a project row.  Used by ``require_project_owner``
        so that missing projects return 404 rather than silently materialising.
        """
        async with self.db_client() as session:
            async with session.begin():
                query = select(Project).where(Project.project_id == project_id)
                result = await session.execute(query)
                return result.scalar_one_or_none()

    async def get_project_or_create_one(self, project_id: int):
        # try:
            async with self.db_client() as session:
                async with session.begin():
                    query = select(Project).where(Project.project_id == project_id)
                    result = await session.execute(query)
                    project = result.scalar_one_or_none()

                    if project is None:
                        project_record = Project(
                            project_id=project_id
                        )
                        project = await self.create_project(project=project_record)
                    return project

    async def get_all_projects(self, page: int=1, page_size: int=10):
        async with self.db_client() as session:
            async with session.begin():
                # count total number of documents
                total_documents = await session.execute(select(
                    func.count(Project.project_id)
                    ))
                total_documents = total_documents.scalar_one()

                # calculate total number of pages
                total_pages = total_documents // page_size
                if total_documents % page_size > 0:
                    total_pages += 1
                
                query = select(Project).order_by(Project.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
                result = await session.execute(query)
                projects = result.scalars().all()

                return projects, total_pages

