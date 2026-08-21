from .BaseController import BaseController
from .ProjectController import ProjectController
import os
try:
    from langchain_community.document_loaders import TextLoader, PyMuPDFLoader
except ImportError:
    TextLoader = None
    PyMuPDFLoader = None
from models import ProcessingEnum
import logging
from typing import List
from dataclasses import dataclass

@dataclass
class Document:
    page_content: str
    metadata: dict

logger = logging.getLogger("uvicorn.error")

try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except ImportError:
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError:
        RecursiveCharacterTextSplitter = None

try:
    import tiktoken
    def _tiktoken_len(text: str) -> int:
        tokenizer = tiktoken.get_encoding("cl100k_base")
        return len(tokenizer.encode(text, disallowed_special=()))
except Exception:
    def _tiktoken_len(text: str) -> int:
        return max(1, len(text) // 4)


class ProcessController(BaseController):
    def __init__(self, project_id: str):
        super().__init__()
        self.project_id = project_id
        self.project_path = ProjectController().get_project_path(project_id=project_id)

    def get_file_extension(self, file_id: str) -> str:
        return os.path.splitext(file_id)[-1] 

    def get_file_loader(self, file_id: str):
        file_extension = self.get_file_extension(file_id=file_id)
        file_path = os.path.join(self.project_path, file_id)

        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None

        if file_extension == ProcessingEnum.TXT.value:
            return TextLoader(file_path=file_path, encoding="utf-8")
        elif file_extension == ProcessingEnum.PDF.value:
            return PyMuPDFLoader(file_path=file_path)
        return None

    def get_file_content(self, file_id: str):
        file_loader = self.get_file_loader(file_id=file_id)
        if file_loader:
            return file_loader.load()
        return None

    def process_file_content(self, file_content: list, file_id: str, 
                            chunk_size: int = 100, chunk_overlap: int = 20):
        """Token-aware chunking using LangChain RecursiveCharacterTextSplitter (P5.1)."""
        if not file_content:
            return []

        if RecursiveCharacterTextSplitter is not None:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=_tiktoken_len,
                separators=["\n\n", "\n", ". ", " ", ""],
            )

            chunks = []
            for record in file_content:
                doc_text = getattr(record, "page_content", str(record))
                doc_meta = getattr(record, "metadata", {})
                if not doc_text or not doc_text.strip():
                    continue

                split_texts = text_splitter.split_text(doc_text)
                for split_text in split_texts:
                    if split_text.strip():
                        chunks.append(Document(
                            page_content=split_text.strip(),
                            metadata=doc_meta if isinstance(doc_meta, dict) else {}
                        ))
            return chunks

        # Fallback to simpler splitter if LangChain text_splitter is unavailable
        file_content_text = [
            record.page_content
            for record in file_content
        ]
        file_content_metadata = [
            record.metadata
            for record in file_content
        ]
        return self.process_simpler_splitter(
            texts=file_content_text,
            metadatas=file_content_metadata,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def process_simpler_splitter(self, texts: List[str], metadatas: List[dict], chunk_size: int, chunk_overlap: int = 0, splitter_tag: str="\n"):
        full_text = " ".join(texts)
        lines = [ doc.strip() for doc in full_text.split(splitter_tag) if len(doc.strip()) > 1 ]

        chunks = []
        current_chunk = ""
        doc_metadata = metadatas[0] if metadatas and len(metadatas) > 0 else {}

        for line in lines:
            current_chunk += line + splitter_tag

            if len(current_chunk) >= chunk_size:
                chunks.append(Document(
                    page_content=current_chunk.strip(),
                    metadata=doc_metadata
                ))

                if chunk_overlap > 0 and len(current_chunk) > chunk_overlap:
                    current_chunk = current_chunk[-chunk_overlap:]
                else:
                    current_chunk = ""

        if current_chunk.strip():
            chunks.append(Document(
                page_content=current_chunk.strip(),
                metadata=doc_metadata
            ))

        return chunks



