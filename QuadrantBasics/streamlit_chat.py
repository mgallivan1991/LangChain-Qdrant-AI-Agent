import streamlit as st
import main as main

st.title("Chat with Company PDFs")

# Initialize chat history if it doesn't exist
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Company selection
companies = ["Company A", "Company B", "Company C"]  # You can modify this list as needed
selected_company = st.selectbox("Select Company", companies)

# Initialize vector database for the selected company
db = main.create_qdrant_database(selected_company)

# Display debug information
st.sidebar.write("Debug Information:")
doc_list = main.retrieve_doc_by_metadata(company=selected_company, file_name="")
st.sidebar.write(f"Number of documents in collection: {len(doc_list[0]) if doc_list else 0}")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Chat input
if question := st.chat_input("Ask a question about your company's documents"):
    # Display user message
    st.chat_message("user").write(question)
    st.session_state.messages.append({"role": "user", "content": question})
    
    try:
        # Get response
        related_documents = main.retrieve_docs(db, question)
        st.sidebar.write(f"Found {len(related_documents)} related documents")
        
        if not related_documents:
            st.warning("No relevant documents found for your query.")
            answer = "I couldn't find any relevant information in the documents to answer your question."
        else:
            answer = main.question_pdf(question, related_documents)
        
        # Display assistant response
        st.chat_message("assistant").write(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})
    except Exception as e:
        st.error(f"Error processing query: {str(e)}")

# Add a clear chat button
if st.button("Clear Chat History"):
    st.session_state.messages = []
    st.rerun() 