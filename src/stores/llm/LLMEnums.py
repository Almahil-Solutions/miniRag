from enum import Enum

class LLMEnums(Enum):
    # Providers
    OPENAI = "OPENAI"
    COHERE = "COHERE"
    
class OpenAIEnums(Enum):
    # roles for llm
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class CoHereEnums(Enum):
    # roles for llm
    SYSTEM = "SYSTEM"
    USER = "USER"
    ASSISTANT = "CHATBOT"

    # document types for embedding
    DOCUMENT = "search_document"
    QUERY = "search_query"

class DocumentTypesEnum(Enum):
    DOCUMENT = "document"
    QUERY = "query"