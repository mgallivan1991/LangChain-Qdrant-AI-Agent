from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from uuid import uuid4
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models
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


def add_documents_to_vector_db(db, file_path):
    # Create a loader from the file path
    loader = PyPDFLoader(file_path)
    documents = loader.load()

    # Create a text splitter to split the document up into multiple documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=300,
        add_start_index=True
    )

    # Run the text splitter on the uploaded document
    chunked_docs = text_splitter.split_documents(documents)

    print(chunked_docs)
    # TODO READ FROM DATABASE AND DONT UPLOAD FILE IF THE NAME ALREADY EXISTS

    # Add the documents to the qdrant collection
    db.add_documents(chunked_docs)
    return db


def retrieve_doc_by_metadata(company):
    client = QdrantClient(url=url)

    result = client.scroll(
        collection_name=company,
        # scroll_filter=models.Filter(
        #     must=[
        #         models.FieldCondition(
        #             key="city",
        #             match=models.MatchValue(value="London"),
        #         ),
        #         models.FieldCondition(
        #             key="color",
        #             match=models.MatchValue(value="red"),
        #         ),
        #     ]
        # ),
    )

    return result