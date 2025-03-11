import streamlit as st
import main as main
import os

st.title("Upload PDFs to Company Database")

# Company selection
companies = ["Company A", "Company B", "Company C"]  # You can modify this list as needed
selected_company = st.selectbox("Select Company", companies)

# Initialize vector database for the selected company
db = main.create_qdrant_database(selected_company)

# Display debug information
st.sidebar.write("Debug Information:")
doc_list = main.retrieve_doc_by_metadata(company=selected_company, file_name="")
st.sidebar.write(f"Number of documents in collection: {len(doc_list[0]) if doc_list else 0}")

uploaded_file = st.file_uploader(
    "Upload PDF",
    type="pdf",
    accept_multiple_files=False
)

if uploaded_file:
    file_name = uploaded_file.name
    
    # Check if file exists in the selected company's collection
    doc_list = main.retrieve_doc_by_metadata(company=selected_company, file_name=file_name)
    file_exists = len(doc_list[0]) > 0
    
    if file_exists:
        st.error(f"This PDF already exists in {selected_company}'s collection.")
    else:
        try:
            # Save the PDF file
            main.upload_pdf(uploaded_file)
            
            # Add the document to the company's collection
            result = main.add_documents_to_vector_db(db, main.pdfs_directory + file_name, selected_company)
            if result == "Docs added to db":
                st.success(f"PDF successfully uploaded to {selected_company}'s collection")
                # Update document count
                doc_list = main.retrieve_doc_by_metadata(company=selected_company, file_name="")
                st.sidebar.write(f"Updated number of documents: {len(doc_list[0]) if doc_list else 0}")
            else:
                st.warning(result)
        except Exception as e:
            st.error(f"Error uploading file: {str(e)}")