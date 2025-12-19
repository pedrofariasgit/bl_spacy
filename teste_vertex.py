import fitz
import json
import google.generativeai as genai
import streamlit as st


# -----------------------------------------
# 1) EXTRAÇÃO DE TEXTO — PyMuPDF Melhorado
# -----------------------------------------
def extract_text_from_all_pages(pdf_bytes):
    """
    Extrai texto do PDF usando PyMuPDF com maior precisão,
    preservando layout e ordem.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        all_text = []

        for page in doc:
            blocks = page.get_text("blocks")

            # Ordena blocos pela posição na página
            blocks = sorted(blocks, key=lambda b: (b[1], b[0]))

            page_text = "\n".join(block[4] for block in blocks)
            all_text.append(page_text)

        return "\n\n".join(all_text)

    except Exception as e:
        st.error(f"Erro ao ler PDF: {e}")
        return ""


# -----------------------------------------
# 2) FUNÇÃO PRINCIPAL — Modelo Gemini
# -----------------------------------------
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
   - Formato típico: 3 letras + números (ex: MEDUVF628071).
   - **NUNCA** deve ser igual ao Booking.
   - **Nunca** contém apenas números.

2. "Booking No":
   - Geralmente apenas numérico.
   - Pode aparecer como "Booking Ref." ou "Booking".

3. Se houver ambiguidade, escolha o que seguir melhor o padrão.

Agora EXTRAIA em JSON:

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

        # LIMPEZA DO JSON
        text = response.text.strip()
        text = text.replace("```json", "").replace("```", "").strip()

        try:
            json.loads(text)
        except:
            try:
                text = text.replace("\n", "").replace("\r", "")
                json.loads(text)
            except:
                return "{}"

        return text

    except Exception as e:
        st.error(f"Erro ao processar o PDF com o Google Vertex: {e}")
        return "{}"
