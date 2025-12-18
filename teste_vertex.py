import fitz  
import google.generativeai as genai
import streamlit as st

# Função para extrair texto de todas as páginas do PDF
def extract_text_from_all_pages(pdf_bytes):
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            text += page.get_text()
        return text
    except Exception as e:
        st.error(f"Erro ao processar o PDF: {e}")
        return ""
    
# Função para processar o texto com Google Gemini
def find_specific_word_with_gemini(pdf_bytes, model_name="gemini-2.0-flash"):
    try:
        pdf_text = extract_text_from_all_pages(pdf_bytes)

        prompt = f"""
        Eu extraí o seguinte texto de um Bill of Lading:

        {pdf_text}

        Extraia os seguintes campos e retorne em JSON:
        - Booking No
        - B/L No
        - Container/Seals
        - Number of pieces
        - Gross Weight Cargo
        - Measurement
        - NCM
        - WOODEN PACKAGE
        """

        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)

        return response.text

    except Exception as e:
        st.error(f"Erro ao processar o PDF com o Google Vertex: {e}")
        return "{}"
