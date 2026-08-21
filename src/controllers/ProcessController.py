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
        
        file_content_text = [
            record.page_content
            for record in file_content
        ]

        file_content_metadata = [
            record.metadata
            for record in file_content
        ]
        chunks = self.process_simpler_splitter(
            texts=file_content_text,
            metadatas=file_content_metadata,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        return chunks


    def process_simpler_splitter(self, texts: List[str], metadatas: List[dict], chunk_size: int, chunk_overlap: int = 0, splitter_tag: str="\n"):

        full_text = " ".join(texts)

        # split by splitter_tag
        lines = [ doc.strip() for doc in full_text.split(splitter_tag) if len(doc.strip()) > 1 ]

        chunks = []
        current_chunk = ""
        doc_metadata = metadatas[0] if metadatas and len(metadatas) > 0 else {}

        for line in lines:
            current_chunk += line + splitter_tag

            if len(current_chunk) >= chunk_size:
                # append to chunks
                chunks.append(Document(
                    page_content=current_chunk.strip(),
                    metadata=doc_metadata
                ))

                if chunk_overlap > 0 and len(current_chunk) > chunk_overlap:
                    current_chunk = current_chunk[-chunk_overlap:]
                else:
                    current_chunk = ""

        # append last chunk
        if current_chunk.strip():
            chunks.append(Document(
                page_content=current_chunk.strip(),
                metadata=doc_metadata
            ))

        return chunks



