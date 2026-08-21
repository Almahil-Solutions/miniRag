from ..VectorDBInterface import VectorDBInterface
from ..VectorDBEnums import (PgVectorIndexTypeEnums, DistanceMethodEnums, 
                              PgVectorDistanceMethodEnums,PgVectorTableSchemeEnums)
from models import RetrievedDocument
from typing import List
import logging
from sqlalchemy.sql import text as sql_text
import json
import psycopg2
import re

# Allow-list pattern for collection names: must start with a letter/underscore,
# followed by letters, digits, or underscores only.  This prevents SQL injection
# via table-name interpolation in DDL statements where bind params cannot be used.
COLLECTION_NAME_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

class PGVectorProvider(VectorDBInterface):
    def __init__(self,db_client, default_vector_size: int= 786,
                    distance_method: str = DistanceMethodEnums.COSINE.value, index_threshold: int = 100):

        self.db_client = db_client
        self.default_vector_size = default_vector_size

        if distance_method == DistanceMethodEnums.COSINE.value:
            self.distance_method = PgVectorDistanceMethodEnums.COSINE.value
        elif distance_method == DistanceMethodEnums.DOT.value:
            self.distance_method = PgVectorDistanceMethodEnums.DOT.value
        

        self.pgvector_table_prefix= PgVectorTableSchemeEnums._PREFIX.value

        self.logger = logging.getLogger("uvicorn")
    
        self.index_threshold = index_threshold
        self.default_index_name = lambda collection_name: f"{collection_name}_vector_idx"
    
    def _validate_collection_name(self, name: str) -> str:
        """Validate that *name* matches the allow-list pattern so it is safe to
        interpolate into DDL statements where SQLAlchemy bind params cannot be used.
        Raises ValueError for any name that does not match.
        """
        if not COLLECTION_NAME_PATTERN.match(name):
            raise ValueError(
                f"Invalid collection name {name!r}: must match "
                r"'^[a-zA-Z_][a-zA-Z0-9_]*$'"
            )
        return name

    async def connect(self):
        async with self.db_client() as session:
            try:
                async with session.begin():
                    # Apply a per-statement timeout to prevent runaway queries.
                    await session.execute(sql_text("SET statement_timeout = '30s'"))
                    #check if the vector extension is installed
                    is_vector_installed = await session.execute(sql_text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
                    if not is_vector_installed.scalar_one_or_none():
                        # Only create if it does not exist
                        await session.execute(sql_text("CREATE EXTENSION vector"))
                        await session.commit()
            except Exception as e:
                # If the extension already exists or any other error occurs, raise the exception
                self.logger.error(f"Vector extension setup: {str(e)}")
                await session.rollback()

    async def disconnect(self):
        pass

    async def is_collection_exists(self, collection_name: str) -> bool:
        record = None
        async with self.db_client() as session:
            async with session.begin():
                list_table = sql_text(
                    "SELECT * FROM pg_tables WHERE tablename = :collection_name"
                )
                result = await session.execute(list_table, {"collection_name": collection_name})
                record = result.scalar_one_or_none()
        if record:
            return True
        return False




    async def list_all_collections(self) -> List:
        records = None
        async with self.db_client() as session:
            async with session.begin():
                list_table = sql_text(
                    "SELECT tablename FROM pg_tables WHERE tablename LIKE :prefix"
                )
                result = await session.execute(
                    list_table, {"prefix": self.pgvector_table_prefix}
                )
                records = result.scalars().all()
        return records


    

    async def get_collection_info(self, collection_name: str) -> dict:
        async with self.db_client() as session:
            async with session.begin():
                table_info_sql = sql_text(
                    """
                    SELECT schemaname, tablename, tableowner, tablespace, hasindexes 
                    FROM pg_tables WHERE tablename = :collection_name
                    """) 
                count_sql = sql_text(f"SELECT COUNT(*) FROM {collection_name}")
                table_info = await session.execute(table_info_sql, {"collection_name": collection_name})
                count = await session.execute(count_sql)
                table_data = table_info.fetchone()
                if not table_data:
                    return None
                
        return {
            "table_info": {
                "schema_name": table_data[0],
                "table_name": table_data[1],
                "table_owner": table_data[2],
                "table_tablespace": table_data[3],
                "has_indexes": table_data[4]
            },
            "record_count": count.scalar_one()
        }

    
    async def delete_collection(self, collection_name: str):
        async with self.db_client() as session:
            async with session.begin():
                self.logger.info(f"Deleting collection {collection_name}")
                drop_sql = sql_text(f"DROP TABLE IF EXISTS {collection_name}")
                await session.execute(drop_sql)
                await session.commit()
        return True
    
    async def create_collection(self, collection_name: str,
                                embedding_size: int,
                                do_reset: bool = False):
        # Validate before any DDL — collection_name is interpolated into SQL.
        self._validate_collection_name(collection_name)

        if do_reset:
            _ = await self.delete_collection(collection_name)

        is_collection_existed = await self.is_collection_exists(collection_name)

        if not is_collection_existed:
            self.logger.info(f"Creating collection {collection_name}")
            async with self.db_client() as session:
                async with session.begin():
                    create_table_sql = sql_text(f"""
                    CREATE TABLE {collection_name} (
                        {PgVectorTableSchemeEnums.ID.value} BIGSERIAL PRIMARY KEY,
                        {PgVectorTableSchemeEnums.TEXT.value} TEXT,
                        {PgVectorTableSchemeEnums.VECTOR.value} vector({embedding_size}),
                        {PgVectorTableSchemeEnums.METADATA.value} jsonb DEFAULT '{{}}',
                        {PgVectorTableSchemeEnums.CHUNK_ID.value} INTEGER,
                        FOREIGN KEY ({PgVectorTableSchemeEnums.CHUNK_ID.value}) REFERENCES chunks(chunk_id)
                    )
                    """)
                    await session.execute(create_table_sql)
                    await session.commit()
            return True
        return False
    

    async def is_index_exists(self, collection_name: str):
        index_name = self.default_index_name(collection_name)
        async with self.db_client() as session:
            async with session.begin():
                is_index_existed_sql = sql_text("""
                                            SELECT 1 
                                            FROM pg_indexes 
                                            WHERE tablename = :collection_name AND indexname = :index_name
                """)
                result = await session.execute(is_index_existed_sql, {
                    "collection_name": collection_name,
                    "index_name": index_name
                })
                return bool(result.scalar_one_or_none())
        

    async def create_vector_index(self, collection_name: str, index_type: str = PgVectorIndexTypeEnums.HNSW.value):

        is_index_existed = await self.is_index_exists(collection_name)
        if is_index_existed:
            # self.logger.error(f"can't create index in collection {collection_name} because index is already existed")
            return False
        async with self.db_client() as session:
            async with session.begin():
                count_sql = sql_text(f"SELECT COUNT(*) FROM {collection_name}")
                count = await session.execute(count_sql)
                record_count = count.scalar_one()
                if record_count < self.index_threshold:
                    return False
                self.logger.info(f"START: Creating index for collection {collection_name}")
                index_name = self.default_index_name(collection_name)

                create_index_sql = sql_text(f"CREATE INDEX {index_name} ON {collection_name} "
                    f"USING {index_type} ({PgVectorTableSchemeEnums.VECTOR.value} {self.distance_method})")
                await session.execute(create_index_sql)

                self.logger.info(f"End: Created index for collection {collection_name}")
        return True

    async def reset_vector_index(self, collection_name: str, index_type: str = PgVectorIndexTypeEnums.HNSW.value):

        index_name = self.default_index_name(collection_name)
        async with self.db_client() as session:
            async with session.begin():
                drop_index_sql = sql_text(f"DROP INDEX IF EXISTS {index_name}")
                await session.execute(drop_index_sql)
                await session.commit()

        return await self.create_vector_index(collection_name=collection_name, index_type=index_type)

    async def insert_one(self, collection_name: str, text: str, vector: list,
                            metadata: dict = None,
                            record_id: str = None):
        # Validate before any DML — collection_name is interpolated into SQL.
        self._validate_collection_name(collection_name)

        is_collection_existed = await self.is_collection_exists(collection_name)
        if not is_collection_existed:
            self.logger.error(f"can't insert new record into collection {collection_name} because it doesn't exist")
            return False
        if not record_id:
            self.logger.error(f"can't insert new record into collection without record_id(chunk_id) for {collection_name}")
            return False

        async with self.db_client() as session:
            async with session.begin():
                insert_sql = sql_text(f"""
                    INSERT INTO {collection_name} 
                        ({PgVectorTableSchemeEnums.TEXT.value}, {PgVectorTableSchemeEnums.VECTOR.value},
                        {PgVectorTableSchemeEnums.METADATA.value}, {PgVectorTableSchemeEnums.CHUNK_ID.value})
                    VALUES (:text, :vector, :metadata, :chunk_id)
                """)
                metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata is not None else "{}"

                await session.execute(insert_sql, {
                    "text": text,
                    "vector": "[" + ",".join([str(v) for v in vector]) + "]", # pgvector only support this format(vector as string) "[1,2,3...n]"
                    "metadata": metadata_json, 
                    "chunk_id": record_id
                })
                await session.commit()
        
        _ = await self.create_vector_index(collection_name=collection_name)
        return True



    

    async def insert_many(self, collection_name: str, texts: list, 
            vectors: list, metadata: list = None,record_ids: list = None, batch_size: int = 50):
        # Validate before any DML — collection_name is interpolated into SQL.
        self._validate_collection_name(collection_name)

        is_collection_existed = await self.is_collection_exists(collection_name)
        if not is_collection_existed:
            self.logger.error(f"can't insert new records into collection {collection_name} because it doesn't exist")
            return False
        
        if len(vectors) != len(record_ids):
            self.logger.error(f"Invalid data items for collection : {collection_name}")
            return False
        if not metadata or len(metadata) == 0:
            metadata = [None] * len(texts)
        try:
            async with self.db_client() as session:
                async with session.begin():
                    for i in range(0, len(texts), batch_size):
                        batch_end = i + batch_size
                        batch_texts = texts[i:batch_end]
                        batch_vectors = vectors[i:batch_end]
                        batch_metadata = metadata[i:batch_end]
                        batch_record_ids = record_ids[i:batch_end]

                        values = []

                        for _texts, _vectors, _metadata, _record_id in zip(batch_texts, batch_vectors, batch_metadata, batch_record_ids):
                            metadata_json = json.dumps(_metadata, ensure_ascii=False) if _metadata is not None else "{}"
                            values.append({
                                "text": _texts,
                                "vector": "[" + ",".join([str(v) for v in _vectors]) + "]",
                                "metadata": metadata_json,
                                "chunk_id": _record_id
                            })
                        
                        batch_insert_sql = sql_text(f"""
                            INSERT INTO {collection_name} 
                                ({PgVectorTableSchemeEnums.TEXT.value}, {PgVectorTableSchemeEnums.VECTOR.value}, 
                                {PgVectorTableSchemeEnums.METADATA.value}, {PgVectorTableSchemeEnums.CHUNK_ID.value})
                            VALUES (:text, :vector, :metadata, :chunk_id)
                        """)
                        await session.execute(batch_insert_sql, values)
                _ = await self.create_vector_index(collection_name=collection_name)
                return True
        except Exception as e:
            self.logger.error(f"Error inserting records: {e}")
            return False
        return False
                    
    

    async def search_by_vector(self, collection_name: str, vector: list, limit: int) -> List[RetrievedDocument]:
        # Validate collection_name before interpolating into SQL (DDL identifiers
        # cannot use bind params, so we enforce an allow-list instead).
        self._validate_collection_name(collection_name)

        is_collection_existed = await self.is_collection_exists(collection_name)
        if not is_collection_existed:
            self.logger.error(f"can't search for a record in collection {collection_name} because it doesn't exist")
            return False

        vector_str = "[" + ",".join([str(v) for v in vector]) + "]"
        async with self.db_client() as session:
            async with session.begin():
                # NOTE: collection_name is already validated against the allow-list
                # above (COLLECTION_NAME_PATTERN). `limit` is passed as a bound
                # parameter (:limit) to prevent any numeric injection.
                search_sql = sql_text(
                    f'SELECT {PgVectorTableSchemeEnums.TEXT.value} as text, '
                    f'1 - ({PgVectorTableSchemeEnums.VECTOR.value} <=> :vector) as score '
                    f' FROM {collection_name} '
                    f'ORDER BY score DESC '
                    f'LIMIT :limit'
                )
                result = await session.execute(search_sql, {"vector": vector_str, "limit": limit})

                records = result.fetchall()
                
                return [
                    RetrievedDocument(
                        **{
                            "text": record.text,
                            "score": record.score
                        }
                    )
                    for record in records
                ]

    async def delete_by_record_ids(self, collection_name: str, record_ids: list):
        self._validate_collection_name(collection_name)
        if not await self.is_collection_exists(collection_name) or not record_ids:
            return False
        async with self.db_client() as session:
            async with session.begin():
                del_sql = sql_text(f"""
                    DELETE FROM {collection_name}
                    WHERE {PgVectorTableSchemeEnums.CHUNK_ID.value} = ANY(:record_ids)
                """)
                await session.execute(del_sql, {"record_ids": record_ids})
                await session.commit()
        return True

    async def delete_by_asset_id(self, collection_name: str, asset_id: int):
        self._validate_collection_name(collection_name)
        if not await self.is_collection_exists(collection_name):
            return False
        async with self.db_client() as session:
            async with session.begin():
                del_sql = sql_text(f"""
                    DELETE FROM {collection_name}
                    WHERE {PgVectorTableSchemeEnums.CHUNK_ID.value} IN (
                        SELECT chunk_id FROM chunks WHERE chunk_asset_id = :asset_id
                    )
                """)
                await session.execute(del_sql, {"asset_id": asset_id})
                await session.commit()
        return True