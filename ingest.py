import os
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, UnstructuredFileLoader
from langchain_chroma import Chroma

# Import settings from our centralized config file
from config import settings

def ingest_data():
    """
    Loads documents from the source directory, splits them into chunks,
    creates embeddings, and stores them in a Chroma vector database.
    """
    print("Starting data ingestion process...")

    # --- CHANGED: The logic is now much simpler ---
    # We tell the DirectoryLoader to use the UnstructuredFileLoader for any
    # file it finds. Unstructured handles MD, TXT, PDF, and more automatically.
    loader = DirectoryLoader(
        settings.DOCUMENT_SOURCE_PATH,
        glob="**/*.*", # Load all files in the directory
        loader_cls=UnstructuredFileLoader,
        show_progress=True,
        use_multithreading=True
    )

    documents = loader.load()
    if not documents:
        print("No documents found in the source directory. Exiting.")
        return

    print(f"Loaded {len(documents)} documents.")

    # Split documents into smaller chunks for better retrieval
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200
    )
    texts = text_splitter.split_documents(documents)
    print(f"Split documents into {len(texts)} chunks.")

    # Initialize the OpenAI embedding model
    embeddings = OpenAIEmbeddings(
        model=settings.OPENAI_EMBEDDING_MODEL,
        openai_api_key=settings.OPENAI_API_KEY
    )

    print("Creating vector store and generating embeddings... (This may take a moment)")
    # Create and persist the Chroma vector store
    db = Chroma.from_documents(
        texts, 
        embeddings, 
        persist_directory=settings.VECTOR_STORE_PATH
    )
    
    print("-----------------------------------------")
    print("Data ingestion complete!")
    print(f"Vector store created at: {settings.VECTOR_STORE_PATH}")
    print("-----------------------------------------")


if __name__ == "__main__":
    ingest_data()