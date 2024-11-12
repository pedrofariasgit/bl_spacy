import requests
import hashlib
import pyodbc
import uuid
import os
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
#TOKEN = st.secrets.get("TOKEN", os.getenv("TOKEN"))
TOKEN = os.getenv('TOKEN')
STORAGE_API_URL = "https://api.headsoft.com.br/geral/blob-stream/private"

# Função para calcular o SHA-512 do conteúdo do arquivo
def calculate_file_hash_sha512(file_content):
    sha512_hash = hashlib.sha512()
    for byte_block in iter(lambda: file_content.read(4096), b""):
        sha512_hash.update(byte_block)
    return sha512_hash.hexdigest()

# Função para processar e inserir o arquivo, forçando um novo hash
def process_and_insert_file(uploaded_file, id_processo):
    # Salvar o arquivo enviado pelo usuário como temporário e obter seu nome
    file_name = uploaded_file.name
    file_content = bytearray(uploaded_file.getvalue())
    
    # Modificação no conteúdo para gerar um hash único
    file_content.extend(b"\n#metadata-invisible:force-upload")

    # Calcular o novo hash SHA-512 do conteúdo do arquivo modificado
    file_hash = hashlib.sha512(file_content).hexdigest()
    
    # Pré-verificação do arquivo via API de hash no storage
    headers = {"Authorization": f"Bearer {TOKEN}"}
    pre_check_url = f"{STORAGE_API_URL}/find?hash={file_hash}"
    pre_check_response = requests.get(pre_check_url, headers=headers)

    # Verificar se o hash já existe no storage
    if pre_check_response.status_code == 200 and pre_check_response.json().get("id"):
        st.warning("Este arquivo já existe no storage com GUID(s): " + ", ".join(pre_check_response.json()["id"]))
        return
    
    # Solicitação de link para upload do arquivo
    upload_link_response = requests.get(f"{STORAGE_API_URL}/new/url", headers=headers)
    upload_data = upload_link_response.json()
    upload_url = upload_data["url"]
    guid = upload_data["id"]

    # Upload do arquivo modificado para o storage
    upload_headers = {
        "x-ms-blob-type": "BlockBlob",
        "Accept": "application/pdf",
        "x-ms-tags": f"hash={file_hash}"
    }
    upload_response = requests.put(upload_url, headers=upload_headers, data=file_content)

    if upload_response.status_code == 201:
        st.success("Upload realizado com sucesso no storage.")
    else:
        st.error("Erro no upload do arquivo.")
        return

    # Conectar ao banco de dados e inserir na tabela arq_Dados_Arquivo e arq_Arquivo
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=kpm.sql.headcargo.com.br,9322;'
        'DATABASE=HeadCARGO_KPM_HOMOLOGACAO;'
        'UID=hc_kpm_ti;'
        'PWD=971639DA-D739-4C0F-83D5-6E34037092FD'
    )
    cursor = conn.cursor()

    try:
        # Obter o próximo IdDados_Arquivo e registrar na tabela `arq_Dados_Arquivo`
        cursor.execute("SELECT MAX(IdDados_Arquivo) + 1 FROM arq_Dados_Arquivo")
        next_id_dados_arquivo = cursor.fetchone()[0]

        # Inserir na tabela `arq_Dados_Arquivo` com o novo GUID e hash
        cursor.execute("""
            INSERT INTO arq_Dados_Arquivo (IdDados_Arquivo, GUID, Storage, Tamanho, Hash, Data_Criacao, Content_Type)
            VALUES (?, ?, ?, ?, ?, GETDATE(), ?)
        """, next_id_dados_arquivo, guid, 1, len(file_content), file_hash, "application/pdf")

        # Obter próximo valor para `IdArquivo` e `Codigo`
        cursor.execute("SELECT MAX(IdArquivo) + 1 FROM arq_Arquivo")
        next_id_arquivo = cursor.fetchone()[0] or 818148

        cursor.execute("SELECT MAX(TRY_CAST(Codigo AS INT)) + 1 FROM arq_Arquivo WHERE ISNUMERIC(Codigo) = 1")
        next_codigo = cursor.fetchone()[0] or 818159

        # Gerar o ROW_GUID no SQL
        row_guid = str(uuid.uuid4()).upper()

        # Inserir na tabela `arq_Arquivo`
        cursor.execute("""
            INSERT INTO arq_Arquivo (
                IdArquivo, IdArquivo_Grupo, IdUsuario_Criacao, IdUsuario_Alteracao, Codigo,
                Descricao, Nome, Data_Arquivo, Modelo, Data_Criacao, Data_Alteracao, Ativo,
                Local_Armazenamento, ROW_GUID, Exibir_Portal_Cliente, Solicitar_Verificacao,
                Prazo_Verificacao, IdDados_Arquivo, Dados_Arquivo
            )
            VALUES (?, NULL, ?, NULL, ?, ?, ?, ?, 0, ?, NULL, 1, 1, ?, 0, 0, NULL, ?, NULL)
        """, 
            next_id_arquivo,       # IdArquivo
            162,                   # IdUsuario_Criacao
            next_codigo,           # Codigo
            file_name,             # Descricao
            file_name,             # Nome
            datetime.now(),        # Data_Arquivo
            datetime.now(),        # Data_Criacao
            row_guid,              # ROW_GUID
            next_id_dados_arquivo  # IdDados_Arquivo
        )

        conn.commit()
        st.success(f"Arquivo registrado com sucesso nas tabelas com IdArquivo = {next_id_arquivo}")

        # Selecionar IdProjeto_Atividade baseado em IdProcesso
        cursor.execute("""
            SELECT IdProjeto_Atividade FROM mov_Logistica_House
            WHERE IdLogistica_House = ?
        """, id_processo)
        result = cursor.fetchone()

        if result:
            id_projeto_atividade = result[0]
            # Inserir na tabela `mov_Projeto_Atividade_Arquivo`
            cursor.execute("""
                INSERT INTO mov_Projeto_Atividade_Arquivo (IdArquivo, IdProjeto_Atividade)
                VALUES (?, ?)
            """, next_id_arquivo, id_projeto_atividade)
            conn.commit()
            st.success("Inserção bem-sucedida na tabela mov_Projeto_Atividade_Arquivo.")
        else:
            st.warning("Nenhum IdProjeto_Atividade correspondente encontrado.")

    except pyodbc.IntegrityError as e:
        st.error(f"Erro de integridade no banco de dados: {e}")

    finally:
        cursor.close()
        conn.close()
