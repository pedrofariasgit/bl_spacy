import streamlit as st
import json
import os
import base64

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

# Função para carregar usuários e senhas
def load_users():
    file_path = os.path.join(os.path.dirname(__file__), 'users.json')
    with open(file_path, 'r') as f:
        return json.load(f)

def main():
    st.set_page_config(
        page_title="Login - Sistema de Processamento de BL",
        page_icon="🔒",
        layout="centered",
        initial_sidebar_state="collapsed"
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
        
        /* Esconder o menu lateral na página de login */
        section[data-testid="stSidebar"] {
            display: none;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Adicionar logo
    add_logo()
    
    # Criar um container centralizado para o formulário de login
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("Login")
        users = load_users()
        usernames = [user['username'] for user in users]

        username = st.text_input("Usuário", key="username_input")
        password = st.text_input("Senha", type="password", key="password_input")

        if st.button("Entrar", key="login_button"):
            if username in usernames:
                user = next(user for user in users if user['username'] == username)
                if user['password'] == password:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.switch_page("pages/main.py")
                else:
                    st.error("Senha incorreta")
            else:
                st.error("Usuário não encontrado")

if __name__ == "__main__":
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    
    if not st.session_state['logged_in']:
        main()
    else:
        st.switch_page("pages/main.py") 