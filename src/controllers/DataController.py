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

        if file.content_type not in self.app_settings.FILE_ALLOWED_TYPES:
            return False, ResponceSignal.FILE_TYPE_NOT_SUPPORTED.value

        if file.size > self.app_settings.FILE_MAX_SIZE * self.size_scale:
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


        
        