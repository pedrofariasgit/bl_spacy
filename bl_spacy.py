import os
import fitz  # PyMuPDF para a IA do Google (Vertex)
import google.generativeai as genai
import streamlit as st
import spacy
from spacy.training.example import Example
from spacy.pipeline import SpanFinder
from spacy.pipeline.span_finder import DEFAULT_SPAN_FINDER_MODEL
from dotenv import load_dotenv
from io import BytesIO
import json
import pandas as pd
from insert_postgre import insert_data_postgre
from insert_sqlserver import main_integration  
from db_select import get_process_data
from teste_vertex import find_specific_word_with_gemini
from datetime import datetime
from insert_ncm import process_and_insert_ncm
import base64
from storage_arq import process_and_insert_file
from docx import Document 

# Carregar as variáveis de ambiente
load_dotenv()
#GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY"))

# Configurar a API do Google Vertex
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
else:
    st.error("Chave da API do Google Vertex não encontrada.")

# Função para carregar usuários e senhas
def load_users():
    file_path = os.path.join(os.path.dirname(__file__), 'users.json')
    with open(file_path, 'r') as f:
        return json.load(f)

# Função de login
def login_page():
    st.title("Login")
    users = load_users()
    usernames = [user['username'] for user in users]

    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if username in usernames:
            user = next(user for user in users if user['username'] == username)
            if user['password'] == password:
                st.session_state['logged_in'] = True
            else:
                st.error("Senha incorreta")
        else:
            st.error("Usuário não encontrado")

# Função para converter a imagem em base64
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

# Função para adicionar a logo
def add_logo():
    logo_path = os.path.join(os.path.dirname(__file__), 'logo.png')
    logo_base64 = get_base64_image(logo_path)
    st.markdown(
        f"""
        <style>
        .logo {{
            position: fixed;
            top: 50px;
            left: 10px;
            padding: 10px;
        }}
        </style>
        <div class="logo">
            <img src="data:image/png;base64,{logo_base64}" width="150" height="auto">
        </div>
        """,
        unsafe_allow_html=True
    )

# Função para carregar o modelo spaCy
def load_model():
    try:
        if os.path.exists("modelo_ner"):
            st.write("Carregando IA...")
            return spacy.load("modelo_ner")
        else:
            st.write("Iniciando um novo modelo...")
            nlp = spacy.blank("en")
            config = {
                "threshold": 0.5,
                "spans_key": "my_spans",
                "max_length": None,
                "min_length": None,
                "model": DEFAULT_SPAN_FINDER_MODEL,
            }
            nlp.add_pipe("span_finder", config=config)
            return nlp
    except Exception as e:
        st.error(f"Erro ao carregar o modelo SpaCy: {e}")
        return None

# Carregar o modelo SpaCy
nlp = load_model()

# Funções para extrair texto de diferentes tipos de arquivo
def extract_text_from_pdf(pdf_bytes):
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        st.error(f"Erro ao processar o PDF: {e}")
        return ""

def extract_text_from_word(word_bytes):
    try:
        document = Document(BytesIO(word_bytes))
        return "\n".join([para.text for para in document.paragraphs])
    except Exception as e:
        st.error(f"Erro ao processar o arquivo Word: {e}")
        return ""

def extract_text_from_excel(excel_bytes):
    try:
        excel_data = pd.read_excel(BytesIO(excel_bytes), sheet_name=None)
        text = ""
        for sheet_name, sheet_data in excel_data.items():
            text += sheet_data.to_string(index=False)
        return text
    except Exception as e:
        st.error(f"Erro ao processar o arquivo Excel: {e}")
        return ""

# Função principal
def main_page():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        login_page()  # Exibe a tela de login se o usuário não estiver logado
        return  # Sai da função main_page se o usuário não está logado
    
    st.title("BL/DRAFT - KPM Logistics")

    # Verifica se o modelo foi carregado corretamente
    if not nlp:
        st.error("Não foi possível carregar o modelo SpaCy. Verifique o modelo ou inicie um novo.")
        return

    # Campo de upload de arquivo
    uploaded_file = st.file_uploader("Escolha um arquivo", type=["pdf", "docx", "xls", "xlsx"], key="file_upload_main")
    numero_processo_input = st.text_input("Número do Processo")

    # Verificar se o número do processo foi informado e buscar os dados no banco de dados
    if numero_processo_input:
        db_data = get_process_data(numero_processo_input)
    else:
        db_data = None

    # Processar o arquivo apenas se for carregado
    if uploaded_file:
        file_extension = uploaded_file.name.split(".")[-1].lower()
        
        if file_extension == "pdf":
            pdf_bytes = uploaded_file.read()  # Ler como bytes
            extracted_text = extract_text_from_pdf(pdf_bytes)
            google_data = find_specific_word_with_gemini(pdf_bytes)  # Somente para PDF
        elif file_extension == "docx":
            extracted_text = extract_text_from_word(uploaded_file.read())
            google_data = extracted_text
        elif file_extension in ["xls", "xlsx"]:
            extracted_text = extract_text_from_excel(uploaded_file.read())
            google_data = extracted_text
        else:
            st.error("Tipo de arquivo não suportado.")
            return


        # Processar dados extraídos do Google Vertex apenas para PDF
        try:
            google_data_cleaned = google_data.strip().strip("```json").strip()
            google_data_json = json.loads(google_data_cleaned) if file_extension == "pdf" else {}
        except json.JSONDecodeError:
            google_data_json = {}

        def get_or_set(key, default_value):
            if key not in st.session_state:
                st.session_state[key] = default_value
            return st.session_state[key]

        # Preencher campos via Google Vertex AI
        bill_no = st.text_input("Bill of Lading Number", get_or_set("bill_no", google_data_json.get("B/L No", "")))
        booking = st.text_input("Booking", get_or_set("booking", google_data_json.get("Booking No", google_data_json.get("Booking", ""))))

        # Tratamento para Container/Seals
        container_seals = google_data_json.get("Container/Seals", "")
        if container_seals:
            parts = container_seals.split("/")
            if len(parts) == 2:
                container, seals = parts
            elif len(parts) == 1:
                container, seals = parts[0], ""
            else:
                container, seals = "", ""
        else:
            container, seals = "", ""


        container_input = st.text_input("Container", get_or_set("container", container))
        seals_input = st.text_input("Seals", get_or_set("seals", seals))
        number_pieces = st.text_input("Number of pieces", get_or_set("number_pieces", google_data_json.get("Number of pieces", "")))
        wooden_package = st.text_input("Wooden Package", get_or_set("wooden_package", google_data_json.get("WOODEN PACKAGE", "")))
        gross_weight = st.text_input("Gross Weight Cargo", get_or_set("gross_weight", google_data_json.get("Gross Weight Cargo", "")))
        measurement = st.text_input("Measurement", get_or_set("measurement", google_data_json.get("Measurement", "")))
        ncm = st.text_input("NCM", get_or_set("ncm", google_data_json.get("NCM", "")))

        if db_data:
            port_loading = st.text_input("Port of Loading", get_or_set("port_loading", db_data.get("port_loading", "")))
            port_discharge = st.text_input("Port of Discharge", get_or_set("port_discharge", db_data.get("port_discharge", "")))
            kind_package = st.text_input("Kind of Package", get_or_set("kind_package", db_data.get("kind_package", "")))
            description_packages = st.text_area("Description of Packages", get_or_set("description_packages", db_data.get("description_packages", "")))

        if st.button("Salvar e Treinar Modelo"):
            if db_data:
                try:
                    insert_data_postgre(
                        bill_no, booking, container_input, seals_input, number_pieces, gross_weight, measurement, ncm, wooden_package,
                        port_loading, port_discharge, db_data["final_delivery"], kind_package, 
                        description_packages, numero_processo_input, db_data["idcia"], db_data["idprocesso"]
                    )
                    st.write("Dados inseridos com sucesso no Portal!")
                    if uploaded_file:
                        process_and_insert_file(uploaded_file, db_data["idprocesso"])
                    next_id_conhecimento = main_integration({
                        "idprocesso": db_data["idprocesso"],
                        "bill_no": bill_no,
                        "upload_date": datetime.now(),
                        "numero_processo": numero_processo_input,
                        "booking": booking,  
                        "idcia": db_data["idcia"],
                        "port_loading": port_loading,  
                        "port_discharge": port_discharge,
                        "description_packages": description_packages,
                        "gross_weight": gross_weight,
                        "measurement": measurement,
                        "ncm": ncm,
                        "wooden_package": wooden_package,
                        "number_pieces": number_pieces,
                        "container": container_input,
                        "seals": seals_input,
                        "kind_package": db_data["kind_package"]
                    })
                    st.write("Dados inseridos com sucesso no HeadCargo!")
                    process_and_insert_ncm(ncm, db_data["idprocesso"], next_id_conhecimento)

                    examples = [
                        (value, {"entities": [(0, len(value), label)]})
                        for value, label in [
                            (bill_no, "BILL_NO"),
                            (booking, "BOOKING"),
                            (container_input, "CONTAINER"),
                            (seals_input, "SEALS"),
                            (number_pieces, "NUMBER_PIECES"),
                            (wooden_package, "WOODEN_PACKAGE"),
                            (gross_weight, "GROSS_WEIGHT"),
                            (measurement, "MEASUREMENT"),
                            (ncm, "NCM"),
                            (port_loading, "PORT_LOADING"),
                            (port_discharge, "PORT_DISCHARGE"),
                            (kind_package, "KIND_PACKAGE"),
                            (description_packages, "DESCRIPTION_PACKAGES"),
                        ]
                        if value  
                    ]

                    def train_model(nlp, examples):
                        optimizer = nlp.initialize()
                        for _ in range(20): 
                            for text, annotations in examples:
                                doc = nlp.make_doc(text)
                                example = Example.from_dict(doc, annotations)
                                nlp.update([example], sgd=optimizer)
                        nlp.to_disk("modelo_ner")  

                    train_model(nlp, examples)
                    st.write("Modelo IA treinado com sucesso!")

                except Exception as e:
                    st.error(f"Erro ao inserir dados no PostgreSQL/SQL Server: {e}")

add_logo()

if __name__ == "__main__":
    main_page()
