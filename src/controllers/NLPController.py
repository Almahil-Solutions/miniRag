from .BaseController import BaseController
from models.db_schemes import Project, DataChunk
from stores.llm.LLMEnums import DocumentTypesEnum
from helpers import get_settings
from typing import List
import json
import os


class NLPController(BaseController):
    def __init__(self, vectordb_client, generation_client, embedding_client, template_parser):
        super().__init__()
        self.vectordb_client = vectordb_client
        self.generation_client = generation_client
        self.embedding_client = embedding_client
        self.template_parser = template_parser


    def create_collection_name(self, project_id: str):
        return f"collection_{self.vectordb_client.default_vector_size}_{project_id}".strip()

    async def reset_vector_db_collection(self, project_id: str):
        collection_name = self.create_collection_name(project_id)
        return await self.vectordb_client.delete_collection(collection_name=collection_name)

    async def get_vector_db_collection_info(self, project_id: str):
        collection_name = self.create_collection_name(project_id)
        collection_info = await self.vectordb_client.get_collection_info(collection_name=collection_name)
        return json.loads(
            json.dumps(collection_info, default=lambda x: x.__dict__))

    async def index_into_vector_db(self, project: Project, chunks: List[DataChunk],
                                    chunks_ids:List[int], do_reset: bool = False):
        # step 1 get collection name
        collection_name = self.create_collection_name(project_id=project.project_id)

        # step 2 manage items
        texts = [chunk.chunk_text for chunk in chunks]
        metadata = [ chunk.chunk_metadata for chunk in chunks]

        vectors = self.embedding_client.embed_text(
                            texts=texts, document_type=DocumentTypesEnum.DOCUMENT.value)
        
        # step 3 create collection if not exists
        _ = await self.vectordb_client.create_collection(
                collection_name=collection_name,
                embedding_size=self.embedding_client.embedding_size,
                do_reset=do_reset
            )

        # step 4 insert into db
        _ = await self.vectordb_client.insert_many(
            collection_name=collection_name,
            texts=texts,
            metadata=metadata,
            record_ids=chunks_ids,
            vectors=vectors
        )
        return True

    async def search_vector_db_collection(self, project: Project, text: str, limit: int = 10):
        # step 1 get collection name
        collection_name = self.create_collection_name(project_id=project.project_id)

        # step 2 embed query
        query_vectors = self.embedding_client.embed_text(
                            texts=text, document_type=DocumentTypesEnum.QUERY.value)
        
        if not query_vectors or len(query_vectors) == 0:
            return False

        if isinstance(query_vectors, list) and len(query_vectors) > 0:
            query_vector = query_vectors[0]

        # step 3 search collection
        results = await self.vectordb_client.search_by_vector(collection_name=collection_name, vector=query_vector, limit=limit)

        if not results or len(results) == 0:
            return False

        return results


    async def answer_rag_question(self, project: Project, query: str, limit: int = 10, language: str = "en"):
        answer, full_prompt, chat_history = None, None, None
        
        # step 1 search vector db collection
        retrieved_documents = await self.search_vector_db_collection(project=project, text=query, limit=limit)

        if not retrieved_documents or len(retrieved_documents) == 0:
            return answer, full_prompt, chat_history

        # step 2 construct LLM prompt
        self.template_parser.set_language(language)
        system_prompt = self.template_parser.get("rag", "system_prompt")

        # Wrap each retrieved chunk in explicit delimiters to defend against
        # prompt-injection attacks where document content attempts to override
        # the system instructions.  The LLM is then instructed only to trust
        # content between these markers.
        delimited_chunks = [
            f"[DOCUMENT {idx + 1} START]\n"
            f"{self.generation_client.preprocess_text(doc.text)}\n"
            f"[DOCUMENT {idx + 1} END]"
            for idx, doc in enumerate(retrieved_documents)
        ]

        documents_prompt = "\n".join([
            self.template_parser.get("rag", "document_prompt",
                variables={
                    "doc_num": idx + 1,
                    "chunk_text": delimited_chunks[idx],
                })
            for idx, doc in enumerate(retrieved_documents)
        ])

        footer_prompt = self.template_parser.get("rag", "footer_prompt", variables={
            "user_query": query
        })

        chat_history = [
            self.generation_client.construct_prompt(
                prompt=system_prompt,
                role=self.generation_client.enums.SYSTEM.value,
            )
        ]

        full_prompt = "\n\n".join([documents_prompt, footer_prompt])

        # Cap the assembled prompt to the model's context limit.  We use a rough
        # 4-characters-per-token estimate relative to INPUT_DAFAULT_MAX_CHARACTERS.
        # When over the limit we truncate the documents section so the query +
        # footer always survive intact.
        settings = get_settings()
        if settings.INPUT_DAFAULT_MAX_CHARACTERS:
            max_prompt_chars: int = settings.INPUT_DAFAULT_MAX_CHARACTERS * 4
            if len(full_prompt) > max_prompt_chars:
                self.logger.warning(
                    f"Prompt length {len(full_prompt)} exceeds cap {max_prompt_chars}; "
                    "truncating documents section."
                )
                # Preserve the footer (query) and truncate documents to fit.
                footer_len = len(footer_prompt) + 2  # +2 for "\n\n" separator
                available = max_prompt_chars - footer_len
                documents_prompt = documents_prompt[:available]
                full_prompt = "\n\n".join([documents_prompt, footer_prompt])

        answer = self.generation_client.generate_text(
            prompt=full_prompt,
            chat_history=chat_history,
        )

        if not answer:
            return answer, full_prompt, chat_history

        return answer, full_prompt, chat_history