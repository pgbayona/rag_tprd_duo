#Run this in terminal
#cd "C:\Users\Pamela Bayona\Desktop\Work\DSTI\Python\TPRD rag"



#WTO API key sk-55e07c5dd0654c5388f20138395a9f30

#pip install python-docx
#pip install openai==0.28

import streamlit as st
import openai
import fitz  # PyMuPDF
from docx import Document  # For Word file extraction
import requests
from bs4 import BeautifulSoup
import concurrent.futures

# Function to extract text from an uploaded PDF file
def extract_text_from_pdf(uploaded_file):
    try:
        pdf_bytes = uploaded_file.read()
        if not pdf_bytes:
            return "Error: PDF file is empty or could not be read."
        
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pdf_text = ""
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            pdf_text += page.get_text("text") + "\n"
        doc.close()
        
        if not pdf_text.strip():
            return "Error: No readable text found in the PDF."

        print(f"Extracted PDF Text (First 500 chars):\n{pdf_text[:500]}")  # Debugging
        return pdf_text.strip()
    except Exception as e:
        return f"Error extracting text from PDF: {e}"

# Function to extract text from an uploaded Word file
def extract_text_from_docx(uploaded_file):
    doc = Document(uploaded_file)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text.strip()

# Function to extract text from a URL
def extract_text_from_url(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        text = "\n".join([para.get_text() for para in paragraphs])
        return text.strip()
    except Exception as e:
        return f"Error retrieving content from URL: {e}"

# Function to retrieve relevant information for answering trade policy questions
def retrieve_relevant_information(topic, sources):
    relevant_snippets = []
    extracted_texts = "\n".join([source["content"][:500] for source in sources])
    print(f"Searching topic: {topic}")
    print(f"Extracted text from sources:\n{extracted_texts}")

    for source in sources:
        if topic.lower() in source["content"].lower():
            relevant_snippets.append(f"- {source['title']}: {source['content'][:300]}...")
            if len(relevant_snippets) >= 3:
                break
    
    return "\n".join(relevant_snippets) if relevant_snippets else extracted_texts

# Function to call the OpenAI API synchronously
def generate_answer_with_openai(question, context, api_key, persona, model="gpt-3.5-turbo"):
    client = openai.OpenAI(api_key=api_key)
    personas = {
        "Trade Policy Expert": "You are Trade Policy (TraPo) RAG, an expert AI answering trade policy questions. You love the WTO and the Multilateral Trading System and strongly oppose Trump.",
        "Dummy Politician": "You are a populist politician who hates the WTO and the Multilateral Trading System. You believe in economic nationalism and dislike trade agreements.",
    }
    
    persona_content = personas.get(persona, personas["Trade Policy Expert"])
    print(f"Persona Selected: {persona}")
    print(f"User Question: {question}")
    print(f"Context (First 500 chars):\n{context[:500]}")
    
    if not context.strip():
        context = "No specific content found in the provided documents. Here is the available document content:\n\n" + context
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": persona_content},
                {"role": "user", "content": f"Here is the available document content:\n\n{context}\n\nQuestion: {question}"}
            ],
            max_tokens=750,
            temperature=0.5,
        )
        return f"**Persona: {persona}**\n\n" + response.choices[0].message.content
    except Exception as e:
        return f"Error generating response: {e}"

# Streamlit app
def main():
    st.title("Trade Policy (TraPo) RAG")
    st.write("Upload PDF, Word documents, or provide a URL containing trade policy discussions and ask questions on trade policy.")

    st.markdown("### Chatbot Parameters:")
    st.markdown("- **Model:** `GPT-3.5-turbo`")
    st.markdown("- **Max Tokens:** `750`")
    st.markdown("- **Temperature:** `0.5` (Controls randomness)")
    
    st.markdown("### Choose a Persona:")
    persona = st.selectbox("Select the chatbot's perspective:", ["Trade Policy Expert", "Dummy Politician"], index=0)
    
    if persona == "Trade Policy Expert":
        st.markdown("**Trade Policy Expert**: A knowledgeable trade policy AI that strongly supports the WTO and the Multilateral Trading System. It advocates for global trade agreements and opposes nationalist economic policies.")
    else:
        st.markdown("**Dummy Politician**: A populist politician who opposes the WTO and multilateral trade agreements. Prefers economic nationalism, protectionist policies, and a more isolationist stance on global trade.")
    
    api_key = st.text_input("Enter your OpenAI API key:", type="password")
    if not api_key:
        st.warning("Please enter your OpenAI API key to proceed.")
        return

    uploaded_files = st.file_uploader("Upload trade policy documents (PDF/DOCX)", accept_multiple_files=True, type=["pdf", "docx"])
    url = st.text_input("Enter a URL containing trade policy discussions:")

    sources = []
    if uploaded_files:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = list(executor.map(lambda file: extract_text_from_pdf(file) if file.type == "application/pdf" else extract_text_from_docx(file), uploaded_files))
        for uploaded_file, text in zip(uploaded_files, results):
            sources.append({"title": uploaded_file.name, "content": text})
            print(f"Processed File: {uploaded_file.name}\nExtracted Content:\n{text[:500]}")
        st.success(f"Successfully processed {len(uploaded_files)} file(s).")
    
    if url:
        url_text = extract_text_from_url(url)
        if "Error" not in url_text:
            sources.append({"title": url, "content": url_text})
            st.success("Successfully retrieved content from URL.")
        else:
            st.error(url_text)

    if not sources:
        st.warning("Please upload a document or provide a URL before asking a question.")
        return

    st.session_state.messages = st.session_state.get("messages", [])
    for message in st.session_state.messages:
        st.chat_message(message["role"]).write(message["content"])

    user_input = st.text_input("Ask a follow-up trade policy question:")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        context = retrieve_relevant_information(user_input, sources)
        response = generate_answer_with_openai(user_input, context, api_key, persona)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.chat_message("assistant").write(response)

if __name__ == "__main__":
    main()
