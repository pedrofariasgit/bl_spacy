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
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY")
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
                st.session_state['logged_in'] = False
            else:
                st.error("Senha incorreta")
        else:
            st.error("Usuário não encontrado")

# Função para converter a imagem em base64
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

# ✅ Função para adicionar a logo (fora do main)
def add_logo():
    logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logo.png')
    logo_base64 = get_base64_image(logo_path)
    # Logo na página
    st.markdown(
        f"""
        <style>
        .logo {{
            position: fixed;
            top: 50px;
            left: 10px;
            padding: 10px;
        }}
        /* Ajustar logo no sidebar */
        .sidebar-logo {{
            margin-bottom: 20px;
            text-align: center;
        }}
        .sidebar-logo img {{
            max-width: 150px;
            width: 100%;
            margin: 0 auto;
        }}
        </style>
        <div class="logo">
            <img src="data:image/png;base64,{logo_base64}" width="150" height="auto">
        </div>
        """,
        unsafe_allow_html=True
    )
    return logo_base64

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
def main():
    st.set_page_config(
        page_title="Sistema de Processamento de BL",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.markdown("""
    <style>
    /* Esconde o nome da página no header */
    header[data-testid="stHeader"] div:first-child {
        display: none;
    }

    /* Esconde o menu lateral padrão do Streamlit (páginas da pasta /pages) */
    section[data-testid="stSidebar"] ul {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)


    # Verificar login
    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        st.session_state['logged_in'] = False
        st.experimental_rerun()
        return
    
    # Carregar o modelo SpaCy
    nlp = load_model()

    # E depois verifica se está ok
    if not nlp:
        st.error("Não foi possível carregar o modelo SpaCy.")
        return
    
    # Adicionar logo na página e pegar o base64 para o menu
    logo_base64 = add_logo()
    
    # Menu lateral com logo
    with st.sidebar:
        # Adicionar logo no topo do sidebar
        st.markdown(f"""
            <div class="sidebar-logo">
                <img src="data:image/png;base64,{logo_base64}">
            </div>
        """, unsafe_allow_html=True)
        
        st.title("Menu")
        menu_option = st.radio(
            "",
            ["Histórico", "Lançar Novo Draft"],
            index=1,
            label_visibility="collapsed"
        )
        
    
    # Navegação baseada na seleção do menu
    if menu_option == "Histórico":
        st.switch_page("pages/main.py")
    else:
        # Resto do código do formulário...
        st.title("Formulário de Lançamento de Draft")
        
        # Campo de upload de arquivo
        uploaded_file = st.file_uploader("Escolha um arquivo", type=["pdf", "docx", "xls", "xlsx"], key="file_upload_main")
        numero_processo_input = st.text_input("Número do Processo", key="process_number_input")

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

            # Definindo container, seals e number_pieces
            container_seals = google_data_json.get("Container/Seals", "")
            container_seals = str(container_seals) if container_seals is not None else ""

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

            number_pieces = google_data_json.get("Number of pieces", "")

            # Criando duas colunas para o grid principal
            col1, col2 = st.columns(2)
            
            with col1:
                bill_no = st.text_input("Bill of Lading Number", get_or_set("bill_no", google_data_json.get("B/L No", "")), key="bill_no_input")
                booking = st.text_input("Booking", get_or_set("booking", google_data_json.get("Booking No", google_data_json.get("Booking", ""))), key="booking_input")
                wooden_package = st.text_input("Wooden Package", get_or_set("wooden_package", google_data_json.get("WOODEN PACKAGE", "")), key="wooden_package_input")
                gross_weight = st.text_input("Gross Weight Cargo", get_or_set("gross_weight", google_data_json.get("Gross Weight Cargo", "")), key="gross_weight_input")
                measurement = st.text_input("Measurement", get_or_set("measurement", google_data_json.get("Measurement", "")), key="measurement_input")

            with col2:
                ncm = st.text_input("NCM", get_or_set("ncm", google_data_json.get("NCM", "")), key="ncm_input")
                if db_data:
                    port_loading = st.text_input("Port of Loading", get_or_set("port_loading", db_data.get("port_loading", "")), key="port_loading_input")
                    port_discharge = st.text_input("Port of Discharge", get_or_set("port_discharge", db_data.get("port_discharge", "")), key="port_discharge_input")
                    kind_package = st.text_input("Kind of Package", get_or_set("kind_package", db_data.get("kind_package", "")), key="kind_package_input")

            # Campo de descrição em largura total
            if db_data:
                description_packages = st.text_area("Description of Packages", get_or_set("description_packages", db_data.get("description_packages", "")), key="description_packages_input")

            st.markdown("---")
            st.subheader("Containers")
            
            # Inicializa a lista de containers na session_state se não existir
            if 'containers' not in st.session_state:
                # Preenche o primeiro container com os dados da IA
                st.session_state.containers = [{
                    'container': container,
                    'seals': seals,
                    'id_equipamento_maritimo': None,  # Será selecionado pelo usuário
                    'quantity': number_pieces,  # Usando o número de peças como quantidade
                    'type_packages': kind_package,  # Usando o tipo de pacote do banco
                    'tipo_item_carga': 1,
                    'gross_weight': gross_weight,
                    'measurement': measurement,
                    'situacao_devolucao': 4,
                    'consolidacao': 2  # Default para "Não"
                }]
            
            # Botão para adicionar novo container
            if st.button("+ Adicionar Container"):
                st.session_state.containers.append({
                    'container': '',
                    'seals': '',
                    'id_equipamento_maritimo': None,
                    'quantity': '',
                    'type_packages': '',
                    'tipo_item_carga': 1,
                    'gross_weight': '',
                    'measurement': '',
                    'situacao_devolucao': 4,
                    'consolidacao': 2
                })
            
            # Lista para armazenar os containers
            containers_list = []
            
            container_to_remove = None

            # Interface para cada container
            for i, container_data in enumerate(st.session_state.containers):
                with st.expander(f"Container {i+1}", expanded=True):
                    col1, col2 = st.columns(2)
                    
                    # Define as opções de equipamento marítimo
                    equipment_options = [
                        ("20 TANK", 1),
                        ("20 PLATAFORM", 2),
                        ("20 DRY BOX", 3),
                        ("20 OPEN TOP", 4),
                        ("20 FLAT RACK", 5),
                        ("20 REEFER", 6),
                        ("40 PLATAFORM", 7),
                        ("40 FLAT RACK", 8),
                        ("40 HIGH CUBE", 9),
                        ("40 DRY BOX", 10),
                        ("40 OPEN TOP", 11),
                        ("40 REEFER", 12),
                        ("20 DRY S.TESTADO", 14),
                        ("40 DRY S.TESTADO", 15),
                        ("40 HC S.TESTADO", 16),
                        ("40 NOR", 17),
                        ("20 ESPECIAL (FR/PL/OT)", 18),
                        ("40 ESPECIAL (FR/PL/OT)", 19),
                        ("40 TANK", 20),
                        ("CARRETA", 21),
                        ("20 NOR", 22)
                    ]
                    
                    with col1:
                        container_input = st.text_input(
                            "Número do Container",
                            key=f"container_{i}",
                            value=container_data['container']
                        )
                        seals_input = st.text_input(
                            "Seals",
                            key=f"seals_{i}",
                            value=container_data['seals']
                        )
                        id_equipamento = st.selectbox(
                            "Tipo de Equipamento",
                            key=f"equipamento_{i}",
                            options=equipment_options,
                            format_func=lambda x: x[0],
                            index=[x[1] for x in equipment_options].index(container_data['id_equipamento_maritimo']) if container_data['id_equipamento_maritimo'] else 0
                        )
                        quantity_input = st.text_input(
                            "Quantidade",
                            key=f"quantity_{i}",
                            value=container_data['quantity']
                        )
                        type_packages_input = st.text_input(
                            "Tipo de Pacotes",
                            key=f"type_packages_{i}",
                            value=container_data['type_packages']
                        )
                    
                    with col2:
                        gross_weight_input = st.text_input(
                            "Peso Bruto",
                            key=f"gross_weight_{i}",
                            value=container_data['gross_weight']
                        )
                        measurement_input = st.text_input(
                            "Medida",
                            key=f"measurement_{i}",
                            value=container_data['measurement']
                        )
                    
                    # Botão para remover container
                    if st.button("Remover Container", key=f"remove_{i}"):
                        container_to_remove = i

                    
                    # Atualiza os dados do container na session_state
                    st.session_state.containers[i] = {
                        'container': container_input,
                        'seals': seals_input,
                        'id_equipamento_maritimo': id_equipamento[1],
                        'quantity': quantity_input,
                        'type_packages': type_packages_input,
                        'tipo_item_carga': 1,
                        'gross_weight': gross_weight_input,
                        'measurement': measurement_input,
                        'situacao_devolucao': 4,
                        'consolidacao': 2
                    }
                    
                    # Adiciona à lista de containers
                    containers_list.append(st.session_state.containers[i])

            if container_to_remove is not None:
                st.session_state.containers.pop(container_to_remove)
                st.rerun()


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
                        
                        # Processa cada container
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
                            "containers": containers_list,
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


if __name__ == "__main__":
    main()
