from abc import ABC, abstractmethod
from typing import List, Union
from dataclasses import dataclass


class LLMInterface(ABC):

    @abstractmethod # to force any inheriting classes to implement this method
    def set_generation_model(self, model_id: str):
        pass

    @abstractmethod
    def set_embedding_model(self, model_id: str):
        pass
    
    @abstractmethod
    def generate_text(self, 
        prompt: str,
        chat_history: List=[],
        max_output_tokens: int = None,
        temperature: float = None, # controls the randomness of the output, 0 is deterministic (close to fact based), 1 is random (more creative)
    ):
        pass

    @abstractmethod
    def generate_text_stream(self,
        prompt: str,
        chat_history: List=[],
        max_output_tokens: int = None,
        temperature: float = None,
    ):
        pass

    @abstractmethod
    def embed_text(self, 
        texts: Union[str, List[str]], 
        document_type: str = None, # some providers embed the text in the context of the type of input(e.g. document, user query etc.) to give a better embedding
    ):
        pass

    @abstractmethod
    def construct_prompt(self, prompt: str, role: str):
        # to make a prompt that is more appropriate for the role of the llm, e.g. system role, user role, etc.
        # here prompt can be from user, system, or assistant(response from previous llm generation like history, RAG context, etc.)
        # the function will take the prompt and role and return a formatted prompt 
        pass

