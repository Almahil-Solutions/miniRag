from ..LLMInterface import LLMInterface
from ..LLMEnums import CoHereEnums, DocumentTypesEnum
import logging
try:
    import cohere
except ImportError:
    cohere = None
from typing import List, Union
import time


class CoHereProvider(LLMInterface):
    def __init__(self, api_key: str,
        default_input_max_characters: int=1000,
        default_generation_output_max_tokens: int=1000,
        default_generation_temperature: float=0.1,):

        self.api_key = api_key
        self.default_input_max_characters = default_input_max_characters
        self.default_generation_output_max_tokens = default_generation_output_max_tokens
        self.default_generation_temperature = default_generation_temperature
        self.generation_model_id = None
        self.embedding_model_id = None
        self.embedding_size = None
        self.client = cohere.Client(api_key=self.api_key)
        self.enums = CoHereEnums
        self.logger = logging.getLogger(__name__)


    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id


    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size


    def preprocess_text(self, text: str):
        return text[:self.default_input_max_characters].strip()


    def generate_text(self, prompt: str, chat_history: list=[],max_output_tokens: int=None, temperature: float=None,):
        if not self.client:
            self.logger.error("Cohere client not initialized")
            return None

        if not self.generation_model_id:
            self.logger.error("generation model for Cohere not set")
            return None

        max_output_tokens = max_output_tokens if max_output_tokens else self.default_generation_output_max_tokens
        temperature = temperature if temperature else self.default_generation_temperature

        response = self.client.chat(
            model=self.generation_model_id,
            chat_history=chat_history,
            message=self.preprocess_text(prompt),
            max_tokens=max_output_tokens,
            temperature=temperature,
        )

        if not response or not response.text:
            self.logger.error("Error while generating text using Cohere API")
            return None

        return response.text

    def generate_text_stream(self, prompt: str, chat_history: list = [], max_output_tokens: int = None, temperature: float = None):
        if not self.client:
            self.logger.error("Cohere client not initialized")
            return
        if not self.generation_model_id:
            self.logger.error("generation model for Cohere not set")
            return

        max_output_tokens = max_output_tokens if max_output_tokens else self.default_generation_output_max_tokens
        temperature = temperature if temperature else self.default_generation_temperature

        try:
            response = self.client.chat_stream(
                model=self.generation_model_id,
                chat_history=chat_history,
                message=self.preprocess_text(prompt),
                max_tokens=max_output_tokens,
                temperature=temperature,
            )
            for event in response:
                # 1) Direct event.text attribute (e.g. text-generation)
                if hasattr(event, "text") and event.text:
                    yield event.text
                # 2) Delta message content text (Cohere v5+ / v2 chat stream)
                elif hasattr(event, "delta") and hasattr(event.delta, "message") and hasattr(event.delta.message, "content"):
                    content = event.delta.message.content
                    if hasattr(content, "text") and content.text:
                        yield content.text
                # 3) event_type == "text-generation"
                elif hasattr(event, "event_type") and event.event_type == "text-generation" and hasattr(event, "text"):
                    yield event.text
                # 4) type == "content-delta"
                elif getattr(event, "type", None) == "content-delta" and hasattr(event, "delta"):
                    delta = event.delta
                    if hasattr(delta, "text") and delta.text:
                        yield delta.text
                    elif hasattr(delta, "message") and hasattr(delta.message, "content") and hasattr(delta.message.content, "text"):
                        yield delta.message.content.text
        except Exception as exc:
            self.logger.error(f"Cohere streaming error: {exc}")

    def embed_text(self, texts: Union[str, List[str]], document_type: str = None):
        if not self.client:
            self.logger.error("CoHere client not initialized")
            return None
        if isinstance(texts, str):
            texts = [texts]
        if not self.embedding_model_id:
            self.logger.error("Embedding model for CoHere not set")
            return None

        input_type = CoHereEnums.DOCUMENT.value
        if document_type == DocumentTypesEnum.QUERY.value:
            input_type = CoHereEnums.QUERY.value

        # --- Rate limit config ---
        MAX_REQUESTS_PER_MINUTE = 1900  # Stay safely under 2000
        BATCH_SIZE = 96                 # Cohere max per request is 96 texts
        DELAY_BETWEEN_BATCHES = 60 / MAX_REQUESTS_PER_MINUTE  # seconds per request

        # Split into batches
        batches = [texts[i:i + BATCH_SIZE] for i in range(0, len(texts), BATCH_SIZE)]
        all_embeddings = []

        for i, batch in enumerate(batches):
            retries = 3
            while retries > 0:
                try:
                    response = self.client.embed(
                        model=self.embedding_model_id,
                        texts=[self.preprocess_text(t) for t in batch],
                        input_type=input_type,
                        embedding_types=["float"],
                    )
                    if not response or not response.embeddings:
                        self.logger.error(f"Empty response for batch {i}")
                        return None
                    all_embeddings.extend(response.embeddings.float)
                    break  # success, exit retry loop

                except Exception as e:
                    if "429" in str(e) or "TooManyRequests" in type(e).__name__:
                        wait = 60  # wait a full minute on rate limit hit
                        self.logger.warning(f"Rate limit hit on batch {i}, waiting {wait}s...")
                        time.sleep(wait)
                        retries -= 1
                    else:
                        self.logger.error(f"Error embedding batch {i}: {e}")
                        return None

            # Throttle between batches
            if i < len(batches) - 1:
                time.sleep(DELAY_BETWEEN_BATCHES)

        return all_embeddings   
    
    
    # def embed_text(self, texts: Union[str, List[str]], document_type: str = None):
    #     if not self.client:
    #         self.logger.error("CoHere client not initialized")
    #         return None

    #     if isinstance(texts, str):
    #         texts = [texts]
        
    #     if not self.embedding_model_id:
    #         self.logger.error("Embedding model for CoHere not set")
    #         return None

    #     input_type = CoHereEnums.DOCUMENT.value
    #     if document_type == DocumentTypesEnum.QUERY.value:
    #         input_type = CoHereEnums.QUERY.value

    #     response = self.client.embed(
    #         model=self.embedding_model_id,
    #         texts=[self.preprocess_text(t)  for t in texts ],
    #         input_type=input_type,
    #         embedding_types=["float"],
    #     )

    #     if not response or not response.embeddings:
    #         self.logger.error("Error while embedding text using Cohere API")
    #         return None

    #     return [ f for f in response.embeddings.float]


    def construct_prompt(self, prompt: str, role: str):
        return {"role": role, "text": prompt }