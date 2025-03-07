from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from uuid import uuid4
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

embeddings = OllamaEmbeddings(model="deepseek-r1:1.5b")

url = "localhost:6333"

pdfs_directory = 'pdfs/'

database_list = {}

# DONE Create a list of JSON objects that are db instances and the names of the companies (with the collection in the names
# DONE add the db name to the list in the create_qdrant_database function
# DONE CHANGE DATABASE LIST TO JSON FOR EASIER ACCESS


def create_qdrant_database(company_name):
    # DONE ADD COLLECTION NAME AS COMPANY NAME and pass to DB Creation

    if company_name in database_list.keys():
        return

    docs = []  # put docs here
    vector_db = QdrantVectorStore.from_documents(
        docs,
        embeddings,
        url=url,
        prefer_grpc=True,
        collection_name=company_name,
    )

    database_list[company_name] = vector_db

    return vector_db


def upload_pdf(file):
    with open(pdfs_directory + file.name, "wb") as f:
        f.write(file.getbuffer())


def add_documents_to_vector_db(db, file_path):
    loader = PyPDFLoader(file_path)
    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=300,
        add_start_index=True
    )

    chunked_docs = text_splitter.split_documents(documents)

    print(chunked_docs)
    # TODO READ FROM DATABASE AND DONT UPLOAD FILE IF THE NAME ALREADY EXISTS

    db.add_documents(chunked_docs)
    return db

