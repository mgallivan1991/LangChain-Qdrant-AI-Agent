from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama.llms import OllamaLLM
from uuid import uuid4
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, VectorParams
# from langchain.embeddings import DeepSeekEmbeddings  # Replace with the actual embedding model you're using
import os

template = """
You are an assistant that answers questions. Using the following retrieved information, answer the user question. If you don't know the answer, say that you don't know. Use up to three sentences, keeping the answer concise.
Question: {question} 
Context: {context} 
Answer:
"""


embeddings = OllamaEmbeddings(model="deepseek-r1:1.5b")

model = OllamaLLM(model="deepseek-r1:1.5b")

url = "localhost:6333"

pdfs_directory = 'pdfs/'

database_list = {}

qdrant_client = QdrantClient(url=url)

# DONE Create a list of JSON objects that are db instances and the names of the companies (with the collection in the names
# DONE add the db name to the list in the create_qdrant_database function
# DONE CHANGE DATABASE LIST TO JSON FOR EASIER ACCESS


def create_qdrant_database(company_name):
    # Return existing database instance if already created in this session
    if company_name in database_list:
        return database_list[company_name]

    # Connect to existing collection or create new one
    try:
        # Try to connect to existing collection
        vector_db = QdrantVectorStore(
            client=qdrant_client,
            collection_name=company_name,
            embeddings=embeddings,
        )
    except Exception:
        # If collection doesn't exist, create a new one
        vector_db = QdrantVectorStore.from_documents(
            [],  # Empty docs since we'll add them later
            embeddings,
            url=url,
            prefer_grpc=True,
            collection_name=company_name,
        )

    # Add the database instance to our session cache
    database_list[company_name] = vector_db

    return vector_db


def upload_pdf(file):
    # Write the PDF to a buffer so we can chuck it and upload it to the vector databases
    with open(pdfs_directory + file.name, "wb") as f:
        f.write(file.getbuffer())


def add_documents_to_vector_db(db, file_path, company):
    # Create a loader from the file path
    loader = PyPDFLoader(file_path)
    documents = loader.load()

    # Calculate the file name from the path
    file_name = os.path.basename(file_path)

    doc_list = retrieve_doc_by_metadata(company=company, file_name=file_name)

    if len(doc_list[0]) > 0:
        return "Doc Already Exists"

    # Create a text splitter to split the document up into multiple documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=300,
        add_start_index=True
    )

    # Run the text splitter on the uploaded document
    chunked_docs = text_splitter.split_documents(documents)

    # Prepare metadata
    metadata = {
        "file_name": file_name,
        "company": company
    }

    # Update metadata for each chunk
    for doc in chunked_docs:
        doc.metadata = metadata

    # Convert documents to strings for embedding
    str_docs = [str(doc.page_content) for doc in chunked_docs]
    
    # Generate embeddings
    embedded_docs = embeddings.embed_documents(str_docs)

    # Generate UUIDs for each chunk
    uuids = [str(uuid4()) for _ in range(len(chunked_docs))]

    # Create points with document content in payload
    points = [
        {
            "id": uuids[i],
            "vector": embedded_docs[i],
            "payload": {
                "text": chunked_docs[i].page_content,  # Store the actual text content
                "metadata": chunked_docs[i].metadata  # Store metadata separately
            }
        }
        for i in range(len(chunked_docs))
    ]

    # Add the documents to the qdrant collection
    qdrant_client.upsert(
        collection_name=company,
        points=points
    )
    return "Docs added to db"


def retrieve_doc_by_metadata(company, file_name):
    client = QdrantClient(url=url)

    # query_text = ""
    #
    # query_vector = embeddings.embed_query(query_text)
    #
    # filter = {
    #     "must": [
    #         {"key": "file_name", "match": {"value": file_name}}  # Example filter by 'category'
    #     ]
    # }
    #
    # result = client.search(
    #     collection_name=company,
    #     query_vector=query_vector,
    #     filter=filter
    # )

    result = client.scroll(
        collection_name=company,
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="file_name",
                    match=models.MatchValue(value=file_name),
                ),
            ]
        ),
    )

    print(result)
    return result


def retrieve_docs(db, query, company, k=4):
    # Create a filter for the company metadata using Qdrant models
    search_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="metadata.company",  # Updated to match new payload structure
                match=models.MatchValue(value=company),
            )
        ]
    )
    
    # Get the client from the database
    client = db._client
    
    # Get embeddings for the query
    query_vector = embeddings.embed_query(query)
    
    # Search with metadata filter
    results = client.search(
        collection_name=company,
        query_vector=query_vector,
        query_filter=search_filter,
        limit=k
    )
    
    # Convert results to documents
    documents = []
    for result in results:
        # Create a new Document with the stored text and metadata
        doc = Document(
            page_content=result.payload['text'],
            metadata=result.payload['metadata']
        )
        documents.append((doc, result.score))
    
    return documents


def question_pdf(question, documents):
    # Extract just the documents from document-score tuples if they exist
    if documents and isinstance(documents[0], tuple):
        documents = [doc for doc, score in documents]
    
    context = "\n\n".join([doc.page_content for doc in documents])
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | model

    return chain.invoke({"question": question, "context": context})