from langchain.tools import tool
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

# Import settings from our centralized config file
from config import settings

# --- Tool Definition ---

@tool
def query_knowledge_base(query: str) -> str:
    """
    Use this tool to answer user questions about the company, its culture,
    benefits, and the hiring process. This tool queries a knowledge base
    of internal company documents.
    """
    # Initialize the embedding function
    embedding_function = OpenAIEmbeddings(
        model=settings.OPENAI_EMBEDDING_MODEL,
        openai_api_key=settings.OPENAI_API_KEY
    )

    # Load the persisted vector store
    vector_store = Chroma(
        persist_directory=settings.VECTOR_STORE_PATH, 
        embedding_function=embedding_function
    )

    # Perform a similarity search and retrieve the top 3 most relevant document chunks
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})
    
    # Retrieve relevant documents
    docs = retriever.invoke(query)
    
    # Format the retrieved documents into a single string
    context = "\n\n---\n\n".join([doc.page_content for doc in docs])
    
    return f"Retrieved context:\n{context}"