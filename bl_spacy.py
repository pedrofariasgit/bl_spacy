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
from insert_postgre import insert_data_postgre
from insert_sqlserver import main_integration  
from db_select import get_process_data
from teste_vertex import find_specific_word_with_gemini
from datetime import datetime
from insert_ncm import process_and_insert_ncm
import base64
from storage_arq import process_and_insert_file

# Carregar as variáveis de ambiente
load_dotenv()
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY"))
#GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

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
            nlp = spacy.blank("en")  # Cria um modelo spaCy vazio
            # Adicionando o SpanFinder ao pipeline
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
        return None  # Certifique-se de retornar None se houver erro

# Carregar o modelo SpaCy
nlp = load_model()

# Função para extrair texto da primeira página do PDF
def extract_text_from_all_pages(pdf_bytes):
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        first_page = doc.load_page(0)  # Carrega apenas a primeira página
        text = first_page.get_text()  # Extrai o texto da primeira página
        return text
    except Exception as e:
        st.error(f"Erro ao processar o PDF: {e}")
        return ""

# Função para adicionar spans ao documento com verificações
def add_span(doc, value, label):
    if value and value in doc.text:
        start = doc.text.find(value)
        end = start + len(value)
        if start != -1 and start < len(doc.text) and end <= len(doc.text):  # Verifica se os índices estão corretos
            return (start, end, label)  # Retorna a tupla (start_char, end_char, label)
    return None

# Treinar o modelo com novos exemplos rotulados
def train_model(nlp, examples):
    optimizer = nlp.begin_training()
    for i in range(20):  # Realize múltiplas iterações para melhorar o aprendizado
        for text, annotations in examples:
            doc = nlp.make_doc(text)
            example = Example.from_dict(doc, annotations)
            nlp.update([example], sgd=optimizer)
    nlp.to_disk("modelo_ner")  # Salve o modelo atualizado

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

    # Campo de upload de arquivo aparece primeiro
    uploaded_file = st.file_uploader("Escolha um arquivo PDF", type="pdf")
    numero_processo_input = st.text_input("Número do Processo")

    # Verificar se o número do processo foi informado e buscar os dados no banco de dados
    if numero_processo_input:
        db_data = get_process_data(numero_processo_input)
    else:
        db_data = None

    if uploaded_file or db_data:
        if uploaded_file:
            pdf_bytes = BytesIO(uploaded_file.read())
            google_data = find_specific_word_with_gemini(pdf_bytes)
        else:
            google_data = "{}"

        # Tenta processar o JSON da Google Vertex
        try:
            google_data_cleaned = google_data.strip().strip("```json").strip()
            google_data_json = json.loads(google_data_cleaned)
        except json.JSONDecodeError as e:
            st.error(f"Erro ao processar o PDF, preencha os campos manualmente: {e}")
            google_data_json = {}

        # Função auxiliar para usar st.session_state ao invés de sobrescrever as edições do usuário
        def get_or_set(key, default_value):
            if key not in st.session_state:
                st.session_state[key] = default_value
            return st.session_state[key]

        # Preencher campos via Google Vertex AI
        bill_no = st.text_input("Bill of Lading Number", get_or_set("bill_no", google_data_json.get("B/L No", "")))
        booking = st.text_input("Booking", get_or_set("booking", google_data_json.get("Booking No", google_data_json.get("Booking", ""))))

        # Tratamento para Container/Seals (tentar dividir, mas lidar com erro se o formato for inesperado)
        container_seals = google_data_json.get("Container/Seals", "")
        if container_seals:  # Verifica se container_seals não é None ou vazio
            if "/" in container_seals:
                try:
                    container, seals = container_seals.split('/')
                except ValueError:
                    container, seals = container_seals, ""
            else:
                container = container_seals
                seals = container_seals
        else:
            container = ""
            seals = ""

        container_input = st.text_input("Container", get_or_set("container", container))
        seals_input = st.text_input("Seals", get_or_set("seals", seals))

        # Acessando as chaves corretas para "Number of pieces" e "Wooden Package"
        number_pieces = st.text_input("Number of pieces", get_or_set("number_pieces", google_data_json.get("Number of pieces", "")))
        wooden_package = st.text_input("Wooden Package", get_or_set("wooden_package", google_data_json.get("WOODEN PACKAGE", "")))

        gross_weight = st.text_input("Gross Weight Cargo", get_or_set("gross_weight", google_data_json.get("Gross Weight Cargo", "")))
        measurement = st.text_input("Measurement", get_or_set("measurement", google_data_json.get("Measurement", "")))
        ncm = st.text_input("NCM", get_or_set("ncm", google_data_json.get("NCM", "")))

        # Preencher campos automaticamente se dados do banco de dados foram encontrados
        if db_data:
            port_loading = st.text_input("Port of Loading", get_or_set("port_loading", db_data.get("port_loading", "")))
            port_discharge = st.text_input("Port of Discharge", get_or_set("port_discharge", db_data.get("port_discharge", "")))
            kind_package = st.text_input("Kind of Package", get_or_set("kind_package", db_data.get("kind_package", "")))
            description_packages = st.text_area("Description of Packages", get_or_set("description_packages", db_data.get("description_packages", "")))

        # Tenta processar o JSON da Google Vertex
        try:
            google_data_cleaned = google_data.strip().strip("```json").strip()
            google_data_json = json.loads(google_data_cleaned)
                                   
        except json.JSONDecodeError as e:
            st.error(f"Erro ao processar o JSON: {e}")
            google_data_json = {}

        if st.button("Salvar e Treinar Modelo"):
            if db_data:
                try:
                    insert_data_postgre(
                        bill_no, booking, container_input, seals_input, number_pieces, gross_weight, measurement, ncm, wooden_package,
                        port_loading, port_discharge, db_data["final_delivery"], kind_package, 
                        description_packages, numero_processo_input, db_data["idcia"], db_data["idprocesso"]
                    )
                    st.write("Dados inseridos com sucesso no Portal!")

                    # Realiza o upload do arquivo no storage e insere nas tabelas
                    if uploaded_file:
                        process_and_insert_file(uploaded_file, db_data["idprocesso"])
                    
                    # Obtenha o IdConhecimento_Embarque da integração
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
                    
                    # Chame o process_and_insert_ncm com o next_id_conhecimento
                    process_and_insert_ncm(ncm, db_data["idprocesso"], next_id_conhecimento)

                    # Prepare os exemplos com a estrutura correta
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
                        if value  # Apenas inclua o campo se ele contiver um valor
                    ]

                    # Função para treinar o modelo com os exemplos formatados corretamente
                    def train_model(nlp, examples):
                        optimizer = nlp.initialize()
                        for i in range(20): 
                            for text, annotations in examples:
                                doc = nlp.make_doc(text)
                                example = Example.from_dict(doc, annotations)
                                nlp.update([example], sgd=optimizer)
                        nlp.to_disk("modelo_ner")  

                    # Chame a função train_model com os exemplos formatados corretamente
                    train_model(nlp, examples)
                    st.write("Modelo IA treinado com sucesso!")


                except Exception as e:
                    st.error(f"Erro ao inserir dados no PostgreSQL/SQL Server: {e}")

                return

add_logo()

if __name__ == "__main__":
    main_page()
