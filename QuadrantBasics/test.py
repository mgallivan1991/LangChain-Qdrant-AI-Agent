import qdrant_client.grpc
import main
from qdrant_client import QdrantClient


def test_multiple_collections():
    # Test 1 Create a collection once and only once per company
    company = 'company1'

    main.create_qdrant_database(company)

    print(main.database_list)

    company2 = 'company2'

    main.create_qdrant_database(company2)

    print(main.database_list)

    main.create_qdrant_database(company)

    print(main.database_list)

    if len(main.database_list.keys()) == 2:
        print("Test1: Pass")
    else:
        print("Fail, wrong number of databases created")


def test_load_a_companys_documents():
    # Test 2 Get a company's db and load it

    pdf = 'pdfs/RegistratrionRenewalEmail.pdf'

    db = main.database_list.get('company1')

    main.add_documents_to_vector_db(db, pdf)


def test_retrieve_a_company_documents():
    company = "company1"

    test_result = main.retrieve_doc_by_metadata(company)

    print(test_result)


def run_tests():
    test_multiple_collections()
    test_load_a_companys_documents()
    test_retrieve_a_company_documents()


run_tests()
