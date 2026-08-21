import pytest
from controllers.ProcessController import ProcessController, Document


class TestProcessControllerUnit:
    @pytest.fixture(autouse=True)
    def setup_controller(self):
        self.controller = ProcessController(project_id="test_proj_123")

    def test_get_file_extension(self):
        assert self.controller.get_file_extension("document.pdf") == ".pdf"
        assert self.controller.get_file_extension("notes.txt") == ".txt"
        assert self.controller.get_file_extension("archive.tar.gz") == ".gz"
        assert self.controller.get_file_extension("no_ext") == ""

    def test_empty_chunk_bug_fix(self):
        """P3.3 fix: empty text or whitespace should never produce empty chunks."""
        chunks = self.controller.process_simpler_splitter(
            texts=[""],
            metadatas=[{}],
            chunk_size=100,
            chunk_overlap=0
        )
        assert chunks == []

        chunks_ws = self.controller.process_simpler_splitter(
            texts=["   \n\n   \t  "],
            metadatas=[{}],
            chunk_size=100,
            chunk_overlap=0
        )
        assert chunks_ws == []

    def test_single_line_under_chunk_size(self):
        text = "Short sentence under chunk limit."
        chunks = self.controller.process_simpler_splitter(
            texts=[text],
            metadatas=[{"source": "test.txt"}],
            chunk_size=100,
            chunk_overlap=0
        )
        assert len(chunks) == 1
        assert chunks[0].page_content == text
        assert chunks[0].metadata == {"source": "test.txt"}

    def test_basic_chunking_multiple_chunks(self):
        lines = [f"This is sentence number {i} containing information." for i in range(50)]
        text = "\n".join(lines)
        chunks = self.controller.process_simpler_splitter(
            texts=[text],
            metadatas=[{"source": "multi.txt"}],
            chunk_size=120,
            chunk_overlap=0
        )
        assert len(chunks) > 1
        for chunk in chunks:
            assert isinstance(chunk, Document)
            assert len(chunk.page_content) > 0
            assert chunk.metadata == {"source": "multi.txt"}

    def test_chunk_overlap_preserves_context(self):
        """P3.4 test: chunk_overlap retains the trailing characters from previous chunk."""
        lines = [f"Paragraph {i}: detailed contents for indexing test." for i in range(20)]
        text = "\n".join(lines)
        chunks = self.controller.process_simpler_splitter(
            texts=[text],
            metadatas=[{}],
            chunk_size=80,
            chunk_overlap=25
        )
        assert len(chunks) >= 2

    def test_process_file_content_empty(self):
        chunks = self.controller.process_file_content([], "file_1")
        assert chunks == []

    def test_process_file_content_token_aware(self):
        """P5.1 test: process_file_content produces valid Document objects."""
        doc1 = Document(
            page_content="MiniRAG is an enterprise retrieval-augmented generation engine built on FastAPI.\nIt provides vector search and modular LLM integrations.",
            metadata={"source": "overview.txt"}
        )
        chunks = self.controller.process_file_content([doc1], "overview.txt", chunk_size=50, chunk_overlap=10)
        assert len(chunks) >= 1
        assert all(isinstance(c, Document) for c in chunks)
        assert all(c.page_content for c in chunks)
