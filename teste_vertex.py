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


def find_specific_word_with_gemini(pdf_bytes, model_name='gemini-2.0-flash'):
    try:
        pdf_text = extract_text_from_all_pages(pdf_bytes)

        prompt = f"""
Você é um especialista em leitura de documentos marítimos (Bill of Lading).
Extraia APENAS os campos abaixo, com extrema precisão, seguindo as regras:

### REGRAS IMPORTANTES
1. "Bill of Lading Number" (B/L No):
   - Sempre é um código do armador.
   - Geralmente aparece no topo do documento.
   - Formato típico: 3 letras + vários números (ex: MEDUVF628071).
   - **NUNCA** deve ser igual ao Booking.
   - **Nunca** contém apenas números.

2. "Booking No":
   - É um número normalmente apenas numérico.
   - Pode aparecer como "Booking Ref." ou "Booking".
   - Geralmente aparece nas seções de dados do navio.

3. Se houver ambiguidade, escolha a opção que MELHOR segue o padrão esperado.

Agora EXTRAIA estes campos em JSON:

- Booking No
- Bill of Lading Number (B/L No)
- Container/Seals
- Number of pieces
- Gross Weight Cargo
- Measurement
- NCM
- WOODEN PACKAGE

TEXTO DO PDF:
{pdf_text}

Responda SOMENTE o JSON.
"""

        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)

        # -------------------------------
        # 🔥 LIMPEZA E VALIDAÇÃO DO JSON
        # -------------------------------
        text = response.text.strip()

        text = text.replace("```json", "").replace("```", "").strip()

        try:
            json.loads(text)
        except:
            st.warning("A IA enviou um JSON inválido, tentando corrigir automaticamente...")
            try:
                text = text.replace("\n", "").replace("\r", "")
                json.loads(text)
            except:
                st.error("Não foi possível corrigir o JSON retornado pela IA.")
                return "{}"

        return text

    except Exception as e:
        st.error(f"Erro ao processar o PDF com o Google Vertex: {e}")
        return "{}"
