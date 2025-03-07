from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from uuid import uuid4
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, VectorParams
# from langchain.embeddings import DeepSeekEmbeddings  # Replace with the actual embedding model you're using
import os

embeddings = OllamaEmbeddings(model="deepseek-r1:1.5b")

url = "localhost:6333"

pdfs_directory = 'pdfs/'

database_list = {}

qdrant_client = QdrantClient(url=url)

# DONE Create a list of JSON objects that are db instances and the names of the companies (with the collection in the names
# DONE add the db name to the list in the create_qdrant_database function
# DONE CHANGE DATABASE LIST TO JSON FOR EASIER ACCESS


def create_qdrant_database(company_name):
    # DONE ADD COLLECTION NAME AS COMPANY NAME and pass to DB Creation

    # Don't create the vector database if the company already has one
    if company_name in database_list.keys():
        return

    # Create the shell database with the embeddings passed in from above
    docs = []  # put docs here
    vector_db = QdrantVectorStore.from_documents(
        docs,
        embeddings,
        url=url,
        prefer_grpc=True,
        collection_name=company_name,
    )

    # Add the shell database to the database dictionary base on the number of
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



    metadata = {
        "file_name": file_name,
        "company": company
    }

    for doc in chunked_docs:
        doc.metadata = metadata
    # TODO READ FROM DATABASE AND DONT UPLOAD FILE IF THE NAME ALREADY EXISTS

    str_docs = [
        str(doc)
        for doc in chunked_docs
    ]

    embedded_docs = embeddings.embed_documents(str_docs)

    uuids = [str(uuid4()) for _ in range(len(chunked_docs))]

    points = [
        {
            "id": uuids[i],  # Unique ID for each document chunk
            "vector": embedded_docs[i],
            "payload": chunked_docs[i].metadata  # Include metadata here as part of the payload
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
