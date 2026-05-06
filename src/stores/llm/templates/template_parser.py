import os
import logging


class TemplateParser:
    def __init__(self, language: str= None, default_language: str= 'en'):
        self.logger = logging.getLogger(__name__)
        self.current_path = os.path.dirname(os.path.abspath(__file__))
        self.default_language = default_language
        self.language = None
        self.set_language(language)
        
    def set_language(self, language: str):
        if not language:
            return None
        language_path = os.path.join(self.current_path, "locales", language)

        if os.path.exists(language_path):
            self.language = language
        else:
            self.language = self.default_language

    def get(self, group: str, key: str, variables: dict={}):
        """
        Get template by group and key.
        
        Args:
            group (str): Group of the template.
            key (str): Key of the template.
            variables (dict): Variables to replace in the template.

        Returns:
            str: Template with variables replaced.
        """
        if not group or not key:
            return None

        target_language =  self.language
        group_path = os.path.join(self.current_path, "locales", target_language, f"{group}.py")
        if not os.path.exists(group_path):
            target_language = self.default_language
            group_path = os.path.join(self.current_path, "locales", target_language, f"{group}.py")

        if not os.path.exists(group_path):
            return None

        # import group module
        try:
            module = __import__(f"stores.llm.templates.locales.{target_language}.{group}", fromlist=[group]) # runtime import
        except Exception as e:
            self.logger.error(f"Error while importing group module: {e}")
            return None

        if not module:
            return None

        key_attributes = getattr(module, key)

        return key_attributes.substitute(variables)
        

        
        