import fitz
import json
import google.generativeai as genai
import streamlit as st
try:
    import pytesseract
    from PIL import Image
    import io
    OCR_AVAILABLE = True
except:
    OCR_AVAILABLE = False


pytesseract.pytesseract.tesseract_cmd = r"C:\Users\kpm_t\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"


def extract_text_from_all_pages(pdf_bytes):
    """
    Extrai texto do PDF usando PyMuPDF com maior precisão, 
    preservando layout e ordem.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        all_text = []

        for page in doc:
            # Usa extração por blocos, mais robusta para documentos estruturados
            blocks = page.get_text("blocks")

            # Ordena blocos pela posição Y (de cima para baixo)
            blocks = sorted(blocks, key=lambda b: (b[1], b[0]))

            page_text = "\n".join(block[4] for block in blocks)
            all_text.append(page_text)

        return "\n\n".join(all_text)

    except Exception as e:
        st.error(f"Erro ao ler PDF: {e}")
        return ""


def extract_text_with_ocr(pdf_bytes):
    """Extrai texto via OCR quando o PDF é imagem."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""

        for page in doc:
            pix = page.get_pixmap()
            img_bytes = pix.tobytes("png")

            img = Image.open(io.BytesIO(img_bytes))
            text += pytesseract.image_to_string(img) + "\n"

        return text

    except Exception as e:
        st.error(f"Erro no OCR: {e}")
        return ""

def extract_text_smart(pdf_bytes):
    """Tenta extrair texto usando PyMuPDF; se falhar ou vier pouco texto, usa OCR."""
    text = extract_text_from_all_pages(pdf_bytes)

    # Se estiver no Streamlit Cloud -> SEM OCR
    if not OCR_AVAILABLE:
        return text

    # Se o texto tiver menos que 200 caracteres, provavelmente é imagem
    if len(text.strip()) < 200:
        ocr_text = extract_text_with_ocr(pdf_bytes)
        if len(ocr_text.strip()) > len(text.strip()):
            return ocr_text  

    return text




def find_specific_word_with_gemini(pdf_bytes, model_name='gemini-2.0-flash'):
    try:
        pdf_text = extract_text_smart(pdf_bytes)

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
