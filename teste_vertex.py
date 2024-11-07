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
    
# Função para processar o texto com Google Vertex AI
def find_specific_word_with_gemini(pdf_bytes, model_name='gemini-1.5-pro-001'):
    try:
        # Extraia o texto da primeira página
        pdf_text = extract_text_from_all_pages(pdf_bytes)

        # Construa o prompt para o modelo Gemini
        prompt = f"""
        Eu extraí o seguinte texto de um Bill of Lading (Conhecimento de Embarque): 

        {pdf_text}
        Por favor, extraia os seguintes campos do texto em formato JSON, separando os valores por vírgula caso haja múltiplos valores: 

        - Booking No: Numero da Reserva, numero seguido da palavra Booking.  
        - Bill of Lading Number (B/L No): Número do conhecimento de embarque, geralmente precedido por "Bill of Lading No:" ou "B/L No:". Não tem '/' no meio do valor. 
        - Container/Seals: Número do container seguido do número do lacre, separados por "/", geralmente precedido por "Container No:" ou "Seal No:".
        - Number of pieces: Numero de peças, geralmente um numero, seguido da palavra CARTONS. 
        - Gross Weight Cargo: Peso bruto da carga, geralmente precedido por "Gross Weight:" ou "Weight:".
        - Measurement: Medidas da carga, geralmente precedido por "Measurement:" ou "Dimensions:".
        - NCM: Nomenclatura comum do mercosul, código da mercadoria.
        - WOODEN PACKAGE: aplicação de madeira ou não.

        Exemplo de saída JSON:
        ```json
            "Booking No": "EBKG09687092",
            "B/L No": "QGD1073247",
            "Container/Seals": "SZLU9932791/R4530268",
            "Number_Pieces": "5200 CARTONS",
            "Gross Weight Cargo": "1000.000",
            "Measurement": "50.000",
            "NMC": "071021",
            "Wooden Package": "NOT APPLICABLE"
        ```
        """
    
        # Utilize o modelo Gemini para processar o texto
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)

        # Retorna o texto da resposta diretamente
        return response.text
    except Exception as e:
        st.error(f"Erro ao processar o PDF com o Google Vertex: {e}")
        return "{}"