import pyodbc
import psycopg2
from db_select import get_process_data
import os

# Função para gerar ID sequencial
def generate_sequential_id(current_max_id):
    return current_max_id + 1

# Função para tratar o NCM
def process_ncm(ncm_value):
    ncm_list = []
    if ncm_value:
        ncm_value = ncm_value.strip()  # Remover espaços em branco extras
        # Se o NCM tiver 8 dígitos (formato 0303.63.00), pegar os primeiros 4 dígitos
        if len(ncm_value) == 8 and '.' in ncm_value:
            ncm_list.append(ncm_value[:4])
        # Se o NCM tiver múltiplos valores separados por vírgula, adicionar todos eles (4 dígitos)
        elif ',' in ncm_value:
            ncm_list = list(set([ncm[:4].strip() for ncm in ncm_value.split(',')]))  # Usar set() para evitar duplicados
        else:
            ncm_list.append(ncm_value[:4])  # Caso seja um NCM com 4 dígitos
    return ncm_list


# Função para obter o IdSerpro_NCM
def get_serpro_ncm_id(ncm):
    connection = pyodbc.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};'
            f"SERVER={os.getenv('SQLSERVER_HOST')};"
            f"DATABASE={os.getenv('SQLSERVER_DATABASE')};"
            f"UID={os.getenv('SQLSERVER_USER')};"
            f"PWD={os.getenv('SQLSERVER_PASSWORD')};"
    )
    cursor = connection.cursor()
    query = "SELECT IdSerpro_NCM FROM cad_Serpro_NCM WHERE Codigo = ?"
    cursor.execute(query, ncm)
    result = cursor.fetchone()
    connection.close()
    return result[0] if result else None

# Função para inserir na tabela mov_Bill_Lading_NCM
def insert_ncm_data(ncm_list, idprocesso, id_conhecimento_embarque):
    try:
        connection = pyodbc.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};'
            f"SERVER={os.getenv('SQLSERVER_HOST')};"
            f"DATABASE={os.getenv('SQLSERVER_DATABASE')};"
            f"UID={os.getenv('SQLSERVER_USER')};"
            f"PWD={os.getenv('SQLSERVER_PASSWORD')};"
        )
        cursor = connection.cursor()

        # Recuperar o maior IdBill_Lading_NCM atual
        cursor.execute("SELECT MAX(IdBill_Lading_NCM) FROM mov_Bill_Lading_NCM")
        current_max_id = cursor.fetchone()[0] or 7000

        for ncm in ncm_list:
            serpro_ncm_id = get_serpro_ncm_id(ncm)

            if serpro_ncm_id:
                # Gerar o próximo IdBill_Lading_NCM
                next_id_bill_lading_ncm = generate_sequential_id(current_max_id)

                # Inserir o NCM na tabela mov_Bill_Lading_NCM, agora com IdConhecimento_Embarque
                insert_query = """
                INSERT INTO mov_Bill_Lading_NCM (IdBill_Lading_NCM, IdSerpro_NCM, IdLogistica_House, IdConhecimento_Embarque)
                VALUES (?, ?, ?, ?)
                """
                cursor.execute(insert_query, (next_id_bill_lading_ncm, serpro_ncm_id, idprocesso, id_conhecimento_embarque))
                current_max_id = next_id_bill_lading_ncm

        connection.commit()
        connection.close()
        print(f"Dados inseridos com sucesso na tabela mov_Bill_Lading_NCM!")

    except Exception as e:
        print(f"Erro ao inserir dados na tabela mov_Bill_Lading_NCM: {e}")

# Função principal para processar e inserir NCMs
def process_and_insert_ncm(ncm_value, idprocesso, id_conhecimento_embarque):
    ncm_list = process_ncm(ncm_value)
    if ncm_list:
        insert_ncm_data(ncm_list, idprocesso, id_conhecimento_embarque)