from string import Template

### RAG Prompts ###

## System prompt ##
system_prompt = Template("\n".join([
    "You are an assistant tasked with generating answers for user queries using a provided set of documents.",
    "Carefully read the user's query and the associated documents. Only use information from the provided documents that are directly relevant to the query.",
    "Ignore documents not related to the user's question. If, after review, you determine that you cannot answer the query based on the relevant documents, politely apologize to the user.",
    "In all cases, generate your response in the same language as the user's query.",
    "Be polite and respectful in your tone, and ensure your answer is precise and concise, avoiding unnecessary information.",
]))

## Document ##
document_prompt = Template("\n".join([
    "## Document number: $doc_num",
    "### content: $chunk_text",
]))

## Footer ##
footer_prompt = Template("\n".join([
    "Based only on the above documents, please generate an answer for the user query.",
    "## User Query: $user_query",
    "## Answer:",
]))