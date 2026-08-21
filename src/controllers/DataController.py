import filetype
from .BaseController import BaseController
from fastapi import UploadFile
from models import ResponceSignal
from .ProjectController import ProjectController
import re
import os

class DataController(BaseController):
    def __init__(self):
        super().__init__()
        self.size_scale = 1048576 # to convert MB to bytes


    def validate_upload_file(self, file: UploadFile):
        # Read the initial bytes (magic numbers) to sniff real file type
        header = file.file.read(261)
        file.file.seek(0)

        kind = filetype.guess(header)
        if kind is not None:
            detected_mime = kind.mime
        else:
            # Plain text files have no magic number header; verify UTF-8 decodability
            try:
                header.decode("utf-8")
                detected_mime = "text/plain"
            except UnicodeDecodeError:
                detected_mime = "application/octet-stream"

        if detected_mime not in self.app_settings.FILE_ALLOWED_TYPES:
            return False, ResponceSignal.FILE_TYPE_NOT_SUPPORTED.value

        if file.size and file.size > self.app_settings.FILE_MAX_SIZE * self.size_scale:
            return False, ResponceSignal.FILE_SIZE_EXCEEDED.value

        return True, ResponceSignal.SUCCESS.value

    def clean_file_name(self, file_name: str):
        # remove special characters except _ and .
        file_name = re.sub(r'[^a-zA-Z0-9_.]', '', file_name)

        # remove leading and trailing spaces
        file_name = file_name.strip()

        # replace space with _
        file_name = file_name.replace(" ", "_")
        return file_name
    
    def generate_unique_file_name(self, original_file_name: str, project_id: str):

        random_string = self.generate_random_string()
        project_path = ProjectController().get_project_path(project_id=project_id)
        cleaned_file_name = self.clean_file_name(original_file_name)

        new_file_path = os.path.join(project_path, random_string + "_" + cleaned_file_name)

        while os.path.exists(new_file_path):
            random_string = self.generate_random_string()
            new_file_path = os.path.join(project_path, random_string + "_" + cleaned_file_name)

        return new_file_path, random_string + "_" + cleaned_file_name

    def scan_file_for_malware(self, file_path: str) -> tuple[bool, dict]:
        """Scan a file using ClamAV daemon via INSTREAM protocol.

        Returns (is_clean, scan_metadata).
        If ClamAV is disabled or unavailable, gracefully returns (True, metadata with status).
        """
        import socket
        import struct
        from datetime import datetime, timezone

        scan_meta = {
            "virus_scan": "skipped",
            "scanned_at": datetime.now(timezone.utc).isoformat(),
        }

        if not getattr(self.app_settings, "CLAMAV_ENABLED", False):
            return True, scan_meta

        host = getattr(self.app_settings, "CLAMAV_HOST", "clamav")
        port = getattr(self.app_settings, "CLAMAV_PORT", 3310)

        try:
            with socket.create_connection((host, port), timeout=10) as s:
                s.sendall(b"zINSTREAM\0")
                with open(file_path, "rb") as f:
                    while chunk := f.read(65536):
                        s.sendall(struct.pack("!I", len(chunk)) + chunk)
                s.sendall(struct.pack("!I", 0))  # zero-length chunk signals EOF

                response = s.recv(4096).decode("utf-8", errors="ignore")
                if "FOUND" in response:
                    scan_meta["virus_scan"] = "infected"
                    scan_meta["details"] = response.strip()
                    return False, scan_meta
                elif "OK" in response:
                    scan_meta["virus_scan"] = "clean"
                    return True, scan_meta
                else:
                    scan_meta["virus_scan"] = "unknown"
                    scan_meta["details"] = response.strip()
                    return True, scan_meta
        except Exception as exc:
            scan_meta["virus_scan"] = "scan_error"
            scan_meta["error"] = str(exc)
            return True, scan_meta


        
        