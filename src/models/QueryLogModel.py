from .BaseDataModel import BaseDataModel
from .db_schemes import QueryLog
from sqlalchemy.future import select
from sqlalchemy import func
import uuid


class QueryLogModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client)

    @classmethod
    async def create_instance(cls, db_client):
        instance = cls(db_client=db_client)
        return instance

    async def create_log(
        self,
        user_id: str,
        project_id: int = None,
        endpoint: str = "",
        query_text: str = None,
        result_summary: dict = None,
        status: str = "success",
        latency_ms: int = None,
        ip_address: str = None,
        request_id: str = None,
    ):
        """Persist a single QueryLog entry. All optional fields default to None."""
        log = QueryLog(
            user_id=uuid.UUID(str(user_id)),
            project_id=project_id,
            endpoint=endpoint,
            query_text=query_text,
            result_summary=result_summary,
            status=status,
            latency_ms=latency_ms,
            ip_address=ip_address,
            request_id=request_id,
        )
        async with self.db_client() as session:
            async with session.begin():
                session.add(log)
            await session.commit()
            await session.refresh(log)
        return log

    async def get_logs_for_user(self, user_id: str, page: int = 1, page_size: int = 20):
        """Paginated fetch of QueryLog rows for the given user, newest-first.
        Returns (logs_list, total_pages)."""
        uid = uuid.UUID(str(user_id))
        async with self.db_client() as session:
            async with session.begin():
                total = (await session.execute(
                    select(func.count(QueryLog.log_id)).where(QueryLog.user_id == uid)
                )).scalar_one()
                total_pages = total // page_size + (1 if total % page_size else 0)
                result = await session.execute(
                    select(QueryLog)
                    .where(QueryLog.user_id == uid)
                    .order_by(QueryLog.created_at.desc())
                    .limit(page_size)
                    .offset((page - 1) * page_size)
                )
                logs = result.scalars().all()
        return logs, total_pages

    async def get_all_logs(self, page: int = 1, page_size: int = 50):
        """Admin listing of all QueryLog rows, newest-first. Returns (logs_list, total_pages)."""
        async with self.db_client() as session:
            async with session.begin():
                total = (await session.execute(
                    select(func.count(QueryLog.log_id))
                )).scalar_one()
                total_pages = total // page_size + (1 if total % page_size else 0)
                result = await session.execute(
                    select(QueryLog)
                    .order_by(QueryLog.created_at.desc())
                    .limit(page_size)
                    .offset((page - 1) * page_size)
                )
                logs = result.scalars().all()
        return logs, total_pages

    async def get_monthly_spend(self, user_id: str) -> float:
        """Calculate total LLM spend in USD for the user over the last 30 days."""
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        uid = uuid.UUID(str(user_id))
        total_spend = 0.0

        async with self.db_client() as session:
            async with session.begin():
                result = await session.execute(
                    select(QueryLog.result_summary).where(
                        QueryLog.user_id == uid,
                        QueryLog.created_at >= cutoff,
                    )
                )
                summaries = result.scalars().all()
                for summary in summaries:
                    if isinstance(summary, dict):
                        cost = summary.get("llm_cost") or summary.get("cost") or 0.0
                        try:
                            total_spend += float(cost)
                        except (ValueError, TypeError):
                            pass

        return round(total_spend, 6)
