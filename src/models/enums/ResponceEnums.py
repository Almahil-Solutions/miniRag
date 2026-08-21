from enum import Enum

# NOTE: 'ResponceSignal' has an intentional legacy spelling typo (with 'c' instead of 's').
# Do NOT fix this typo, as it is preserved for backward compatibility across all API consumers
# and stored client states.
class ResponceSignal(Enum):
    SUCCESS = "success"
    FILE_TYPE_NOT_SUPPORTED = "file_type_not_supported"
    FILE_SIZE_EXCEEDED = "file_size_exceeded"
    FILE_NOT_FOUND = "file_not_found"
    FILE_ID_ERROR = "no_file_found_with_given_id"
    FILE_UPLOADED_SUCCESSFULLY = "file_uploaded_successfully"
    FILE_UPLOADED_FAILED = "file_uploaded_failed"
    FILE_PROCESSING_SUCCESSFULL = "file_processing_successfull"
    FILE_PROCESSING_FAILED = "file_processing_failed"
    PROJECT_NOT_FOUND = "project_not_found"
    INSERT_INTO_VECTORDB_ERROR = "insert_into_vector_db_error"
    INSERT_INTO_VECTORDB_SUCCESS = "insert_into_vector_db_success"
    VECTORDB_COLLECTION_RETRIEVED = "vector_db_collection_retrieved"
    VECTORDB_COLLECTION_NOT_RETRIEVED = "vector_db_collection_not_retrieved"
    VECTORDB_SEARCH_ERROR = "vector_db_search_error"
    VECTORDB_SEARCH_SUCCESS = "vector_db_search_success"
    RAG_ANSWER_ERROR = "rag_answer_error"
    RAG_ANSWER_SUCCESS = "rag_answer_success"
    DATA_PUSH_TASK_READY = "data_push_task_started"
    PROCEDD_AND_PUSH_WORKFLOW_READY = "procedd_and_push_workflow_started"
    

