import io
from unittest.mock import MagicMock, patch
import pytest
from controllers.DataController import DataController
from models import ResponceSignal


class TestDataControllerUnit:
    @pytest.fixture(autouse=True)
    def setup_controller(self):
        self.controller = DataController()

    def test_rejects_spoofed_executable(self):
        """P3.2: An executable masquerading as a PDF must be rejected by magic-byte sniffing."""
        # PE/EXE magic number "MZ"
        exe_bytes = b"MZ" + b"\x00" * 300
        mock_file = MagicMock()
        mock_file.filename = "safe_document.pdf"
        mock_file.content_type = "application/pdf"  # Client claims PDF
        mock_file.size = len(exe_bytes)
        mock_file.file = io.BytesIO(exe_bytes)

        is_valid, signal = self.controller.validate_upload_file(file=mock_file)
        assert not is_valid
        assert signal == ResponceSignal.FILE_TYPE_NOT_SUPPORTED.value

    def test_accepts_valid_pdf_magic_bytes(self):
        """P3.2: Valid PDF header is accepted."""
        pdf_bytes = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n" + b"\x00" * 300
        mock_file = MagicMock()
        mock_file.filename = "report.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.size = len(pdf_bytes)
        mock_file.file = io.BytesIO(pdf_bytes)

        is_valid, signal = self.controller.validate_upload_file(file=mock_file)
        assert is_valid
        assert signal == ResponceSignal.SUCCESS.value

    def test_accepts_valid_utf8_text_file(self):
        """P3.2: Plain text with valid UTF-8 encoding is accepted."""
        txt_bytes = "This is a clean plain text knowledge base document.".encode("utf-8")
        mock_file = MagicMock()
        mock_file.filename = "notes.txt"
        mock_file.content_type = "text/plain"
        mock_file.size = len(txt_bytes)
        mock_file.file = io.BytesIO(txt_bytes)

        is_valid, signal = self.controller.validate_upload_file(file=mock_file)
        assert is_valid
        assert signal == ResponceSignal.SUCCESS.value

    def test_rejects_unsupported_file_type(self):
        """Unsupported file extensions / types are rejected."""
        # PNG magic bytes
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 300
        mock_file = MagicMock()
        mock_file.filename = "image.png"
        mock_file.content_type = "image/png"
        mock_file.size = len(png_bytes)
        mock_file.file = io.BytesIO(png_bytes)

        is_valid, signal = self.controller.validate_upload_file(file=mock_file)
        assert not is_valid
        assert signal == ResponceSignal.FILE_TYPE_NOT_SUPPORTED.value

    def test_rejects_oversized_file(self):
        """Files exceeding FILE_MAX_SIZE are rejected."""
        pdf_bytes = b"%PDF-1.4\n" + b"\x00" * 200
        mock_file = MagicMock()
        mock_file.filename = "huge.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.file = io.BytesIO(pdf_bytes)
        # Mock size strictly greater than configured FILE_MAX_SIZE
        mock_file.size = (self.controller.app_settings.FILE_MAX_SIZE + 5) * self.controller.size_scale

        is_valid, signal = self.controller.validate_upload_file(file=mock_file)
        assert not is_valid
        assert signal == ResponceSignal.FILE_SIZE_EXCEEDED.value

    def test_clean_file_name_sanitization(self):
        """Sanitizes special characters, replaces spaces with underscores."""
        assert self.controller.clean_file_name("My Document (1).pdf") == "My_Document_1.pdf"
        assert self.controller.clean_file_name("../../etc/passwd") == "....etcpasswd"
        assert self.controller.clean_file_name("data_file_2026.txt") == "data_file_2026.txt"
        assert self.controller.clean_file_name(" spaced   name .pdf ") == "spaced_name_.pdf"

    def test_scan_file_for_malware_disabled_graceful(self):
        """P4.5: Returns clean when ClamAV is disabled in settings."""
        with patch.object(self.controller.app_settings, "CLAMAV_ENABLED", False):
            is_clean, meta = self.controller.scan_file_for_malware("/tmp/test.pdf")
            assert is_clean
            assert meta["virus_scan"] == "skipped"

    def test_scan_file_for_malware_connection_failure_fails_safe(self):
        """P4.5: ClamAV connection failure gracefully falls back without crashing upload."""
        with patch.object(self.controller.app_settings, "CLAMAV_ENABLED", True):
            with patch("socket.create_connection", side_effect=ConnectionRefusedError("No clamav")):
                is_clean, meta = self.controller.scan_file_for_malware("/tmp/test.pdf")
                assert is_clean
                assert meta["virus_scan"] == "scan_error"
