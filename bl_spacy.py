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
from db_select import get_process_data
from vertex import find_specific_word_with_gemini

load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

# Função para carregar o modelo spaCy
def load_model():
    try:
        if os.path.exists("modelo_ner"):
            st.write("Carregando o modelo treinado...")
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
        st.error(f"Erro ao carregar o modelo spaCy: {e}")
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
            span = doc.char_span(start, end, label=label)
            if span is not None:  # Verifica se o span foi criado corretamente
                return span
    return None

# Função para adicionar spans ao documento com verificações
def add_span(doc, value, label):
    if value and value in doc.text:
        start = doc.text.find(value)
        end = start + len(value)
        if start != -1 and start < len(doc.text) and end <= len(doc.text):  # Verifica se os índices estão corretos
            return (start, end, label)  # Retorna a tupla (start_char, end_char, label)
    return None

# Função principal
def main_page():
    st.title("Importação de BL - KPM Logistics")

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
            st.error(f"Erro ao processar o JSON: {e}")
            google_data_json = {}

        # Função auxiliar para usar st.session_state ao invés de sobrescrever as edições do usuário
        def get_or_set(key, default_value):
            if key not in st.session_state:
                st.session_state[key] = default_value
            return st.session_state[key]

        # Preencher campos via Google Vertex AI
        bill_no = st.text_input("Bill of Lading Number", get_or_set("bill_no", google_data_json.get("B/L No", "")))

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

        gross_weight = st.text_input("Gross Weight Cargo", get_or_set("gross_weight", google_data_json.get("Gross Weight Cargo", "")))
        measurement = st.text_input("Measurement", get_or_set("measurement", google_data_json.get("Measurement", "")))
        ncm = st.text_input("NCM", get_or_set("ncm", google_data_json.get("NCM", "")))
        wooden_package = st.text_input("Wooden Package", get_or_set("wooden_package", google_data_json.get("Wooden Package", "")))

        # Preencher campos automaticamente se dados do banco de dados foram encontrados
        if db_data:
            port_loading = st.text_input("Port of Loading", get_or_set("port_loading", db_data.get("port_loading", "")))
            port_discharge = st.text_input("Port of Discharge", get_or_set("port_discharge", db_data.get("port_discharge", "")))
            final_place = st.text_input("Final Delivery", get_or_set("final_place", db_data.get("final_delivery", "")))
            kind_package = st.text_input("Kind of Package", get_or_set("kind_package", db_data.get("kind_package", "")))
            description_packages = st.text_area("Description of Packages", get_or_set("description_packages", db_data.get("description_package", "")))

        if st.button("Salvar e Treinar Modelo"):
            # Primeiro, realiza o insert no PostgreSQL
            if db_data:
                try:
                    insert_data_postgre(
                        bill_no, container_input, seals_input, gross_weight, measurement, ncm, wooden_package,
                        port_loading, port_discharge, final_place, kind_package, description_packages,
                        numero_processo_input, db_data["idcia"], db_data["idprocesso"]
                    )
                    st.write("Dados inseridos com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao inserir dados no PostgreSQL: {e}")
                    return

            # Em seguida, tenta treinar o modelo SpaCy
            try:
                if uploaded_file:
                    text = extract_text_from_all_pages(pdf_bytes)
                    doc = nlp.make_doc(text)  # Certifique-se de que o texto pertence ao doc

                    spans = []  # Use spans em vez de entidades para evitar conflito de sobreposição

                    # Adicionar spans corretamente ao modelo
                    spans.append(add_span(doc, bill_no, "BILL_NO"))
                    spans.append(add_span(doc, container_input, "CONTAINER"))
                    spans.append(add_span(doc, seals_input, "SEALS"))
                    spans.append(add_span(doc, gross_weight, "GROSS_WEIGHT"))
                    spans.append(add_span(doc, measurement, "MEASUREMENT"))
                    spans.append(add_span(doc, ncm, "NCM"))
                    spans.append(add_span(doc, wooden_package, "WOODEN_PACKAGE"))

                    # Filtrar spans válidos (não nulos)
                    valid_spans = [(start, end, label) for span in spans if span for start, end, label in [span]]

                    # Criar um exemplo do SpaCy e treinar o modelo usando spans, se houver spans válidos
                    if valid_spans:
                        example = Example.from_dict(doc, {"spans": {"my_spans": valid_spans}})
                        losses = {}
                        nlp.update([example], losses=losses)

                        # Exibir as perdas para saber se o modelo está sendo treinado
                        st.write(f"Perdas durante o treinamento: {losses}")

                        # Salvar o modelo
                        nlp.to_disk("modelo_ner")
                        st.success("Modelo salvo e treinado com sucesso!")
                    else:
                        st.warning("Nenhum span válido foi encontrado para treinar o modelo.")

                else:
                    st.error("Erro: O arquivo PDF não foi carregado corretamente.")

            except Exception as e:
                st.error(f"Erro ao salvar ou treinar o modelo: {e}")

if __name__ == "__main__":
    main_page()
