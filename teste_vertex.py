import fitz
import json
import google.generativeai as genai
import streamlit as st


def extract_text_from_all_pages(pdf_bytes):
    """Extrai texto de todas as páginas do PDF usando PyMuPDF."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        return text
    except Exception as e:
        st.error(f"Erro ao ler PDF: {e}")
        return ""


def find_specific_word_with_gemini(pdf_bytes, model_name="gemini-2.0-flash"):
    """Extrai campos específicos do texto do PDF usando Gemini."""

    try:
        pdf_text = extract_text_from_all_pages(pdf_bytes)

        prompt = f"""
Você é um extrator de dados especialista em documentos de transporte internacional.

Leia o texto abaixo extraído de um Bill of Lading e RETORNE SOMENTE um JSON válido.
Nenhum texto explicativo deve ser incluído fora do JSON.

TEXTO DO DOCUMENTO:
----------------------
{pdf_text}
----------------------

EXTRAIA OS CAMPOS ABAIXO:

- Booking No → número da reserva (formas válidas: ABC1234567, EKG98765432, etc.)
- B/L No → número do conhecimento (NUNCA contém "/")
- Container/Seals → número do container e lacre separados por "/"
- Number of pieces → exemplo: "5200 CARTONS"
- Gross Weight Cargo → número decimal (ex: "1000.000")
- Measurement → número decimal (ex: "50.000")
- NCM → código da mercadoria (ex: "071021")
- WOODEN PACKAGE → "APPLICABLE" ou "NOT APPLICABLE"

RETORNE SOMENTE UM JSON VÁLIDO COMO ESTE EXEMPLO:

{{
  "Booking No": "",
  "B/L No": "",
  "Container/Seals": "",
  "Number_Pieces": "",
  "Gross Weight Cargo": "",
  "Measurement": "",
  "NCM": "",
  "WOODEN PACKAGE": ""
}}
"""

        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)

        # Garante retorno limpo
        text = response.text.strip()

        # Remove possíveis marcadores de bloco
        text = text.replace("```json", "").replace("```", "").strip()

        # Tenta validar o JSON
        try:
            json.loads(text)
        except:
            st.warning("A IA enviou um JSON inválido, tentando corrigir automaticamente...")
            try:
                # Pequena correção automática
                text = text.replace("\n", "").replace("\r", "")
                json.loads(text)
            except:
                st.error("Não foi possível corrigir o JSON retornado pela IA.")
                return "{}"

        return text

    except Exception as e:
        st.error(f"Erro ao processar PDF com Gemini: {e}")
        return "{}"
