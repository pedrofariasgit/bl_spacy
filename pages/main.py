import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import psycopg2
import os
import base64
import locale


try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    # Caso o locale não esteja disponível (como no Streamlit Cloud)
    pass

def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

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

def conectar_bd():
    """Conecta ao banco de dados PostgreSQL"""
    try:
        conn = psycopg2.connect(
            dbname="pdf_data",
            user="kpm",
            password="@Kpm<102030>",
            host="89.117.17.6",
            port="5432"
        )
        return conn
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {str(e)}")
        return None

def show_history():
    """Mostra o histórico de lançamentos de draft"""
    st.title("Histórico de Lançamentos de Draft")

    # CSS para deixar os campos de data menores
    st.markdown("""
    <style>
    .small-date-input input {
        max-width: 200px;
    }
    </style>
    """, unsafe_allow_html=True)

    # CSS para ajustar o layout das datas
    st.markdown("""
        <style>
        /* Ajusta o campo de data para ter largura fixa */
        input[type="text"][data-testid="stDateInput"] {
            width: 200px !important;
        }
        
        /* Remove margens e padding desnecessários */
        div[data-testid="column"] {
            padding: 0px !important;
            margin: 0px !important;
        }
        
        /* Ajusta os labels das datas */
        .stDateInput > label {
            margin-bottom: 5px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    data_inicial = st.date_input(
        "Data Inicial",
        datetime(2024, 10, 1),
        key="data_inicial"
    )
    
    data_final = st.date_input(
        "Data Final",
        datetime.now(),
        key="data_final"
    )


        
    # Grid de Resultados
    conn = conectar_bd()
    if conn:
        try:
            query = """
            SELECT 
                numero_processo,
                booking,
                port_loading,
                port_discharge,
                upload_date
            FROM pdf_info
            WHERE upload_date::date BETWEEN %s AND %s
            ORDER BY upload_date DESC
            """
            
            df = pd.read_sql_query(query, conn, params=[data_inicial, data_final])
            
            # Formatar a data
            df['upload_date'] = pd.to_datetime(df['upload_date'], utc=True).dt.strftime('%d/%m/%Y %H:%M')
            
            # Mostrar dados em uma tabela
            st.dataframe(
                df,
                column_config={
                    "numero_processo": "Número do Processo",
                    "booking": "Booking",
                    "port_loading": "Porto de Origem",
                    "port_discharge": "Porto de Destino",
                    "upload_date": "Data de Inserção"
                },
                hide_index=True
            )
            
        except Exception as e:
            st.error(f"Erro ao buscar dados: {str(e)}")
        finally:
            conn.close()

def main():
    st.set_page_config(
        page_title="Sistema de Processamento de BL",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Esconder os nomes das páginas no canto, mas manter o seletor de tema
    st.markdown("""
        <style>
        /* Esconder apenas os nomes das páginas no header, mantendo o seletor de tema */
        header[data-testid="stHeader"] div:nth-child(1) {
            display: none;
        }
        
        /* Esconder os nomes das páginas no sidebar */
        [data-testid="stSidebarNav"] {
            display: none;
        }
        
        /* Ajustar campos de data */
        .stDateInput {
            width: 200px !important;
        }
        
        /* Container para as datas */
        [data-testid="column"] {
            padding: 0px !important;
            margin: 0px !important;
        }
        
        /* Ajustar labels das datas */
        .stDateInput > label {
            padding-right: 10px !important;
        }
        
        /* Reduzir espaço entre os inputs */
        .row-widget {
            min-width: unset !important;
            margin-right: -100px !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Verificar login
    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        st.switch_page("../login.py")
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
            index=0,
            label_visibility="collapsed"
        )
    
    # Navegação baseada na seleção do menu
    if menu_option == "Lançar Novo Draft":
        st.switch_page("pages/draft.py")
    else:
        show_history()

if __name__ == "__main__":
    main() 