import pyodbc
from datetime import datetime
import re
import os

def connect_to_sqlserver():
    try:
        connection = pyodbc.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};'
            f"SERVER={os.getenv('SQLSERVER_HOST')};"
            f"DATABASE={os.getenv('SQLSERVER_DATABASE')};"
            f"UID={os.getenv('SQLSERVER_USER')};"
            f"PWD={os.getenv('SQLSERVER_PASSWORD')};"
        )
        return connection
    except Exception as e:
        print(f"Erro ao conectar ao SQL Server: {e}")

# Função para obter o maior ID atual em uma tabela
def get_max_id_from_table(table_name, id_column):
    try:
        connection = connect_to_sqlserver()
        cursor = connection.cursor()

        query = f"SELECT MAX({id_column}) FROM {table_name}"
        cursor.execute(query)
        result = cursor.fetchone()
        connection.close()

        return result[0] if result[0] is not None else 0  # Retorna 0 se não houver registros

    except Exception as error:
        raise Exception(f"Erro ao buscar o maior ID na tabela {table_name}: {error}")

# Função para obter dados adicionais necessários para o insert
def get_sql_data(idprocesso):
    try:
        connection = connect_to_sqlserver()
        cursor = connection.cursor()

        # Query para obter os campos do SQL Server
        query = """
        SELECT 
            Lhs.IdImportador, Lhs.IdExportador, Lhs.IdNotify, 
            Lhs.IdEmpresa_Sistema, Lms.Tipo_Operacao
        FROM mov_Logistica_House Lhs
        LEFT OUTER JOIN mov_Logistica_Master Lms ON Lms.IdLogistica_Master = Lhs.IdLogistica_Master
        WHERE Lhs.IdLogistica_House = ?
        """
        cursor.execute(query, (idprocesso,))
        result = cursor.fetchone()
        connection.close()

        if result:
            return {
                "IdImportador": result[0],
                "IdExportador": result[1],
                "IdNotify": result[2],
                "IdEmpresa_Sistema": result[3],
                "Tipo_Operacao": result[4]
            }
        else:
            raise Exception(f"Nenhum dado encontrado para IdLogistica_House {idprocesso}")

    except Exception as error:
        raise Exception(f"Erro ao buscar dados no SQL Server: {error}")

# Função para gerar ID sequencial (a partir de um valor base)
def generate_sequential_id(current_max_id, table_name):
    # Incrementa o ID atual para o próximo valor
    return current_max_id + 1

# Função para inserir na tabela mov_Conhecimento_Embarque
def insert_into_conhecimento_embarque(postgre_data, sql_data, next_id_conhecimento):
    try:
        connection = connect_to_sqlserver()
        cursor = connection.cursor()

        insert_query = """
        INSERT INTO mov_Conhecimento_Embarque (IdConhecimento_Embarque, IdLogistica_House, Numero, Data, Numero_Embarque, 
                                               IdImportador, IdExportador, IdNotify, IdEmpresa_Sistema, Tipo_Operacao, Tipo_Conhecimento)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        tipo_conhecimento = 1 

        data = (
            next_id_conhecimento,
            postgre_data["idprocesso"],
            postgre_data["bill_no"],
            postgre_data["upload_date"],
            postgre_data["numero_processo"],
            sql_data["IdImportador"],
            sql_data["IdExportador"],
            sql_data["IdNotify"],
            sql_data["IdEmpresa_Sistema"],
            sql_data["Tipo_Operacao"],
            tipo_conhecimento  # Valor numérico adequado
        )

        cursor.execute(insert_query, data)
        connection.commit()
        connection.close()

    except Exception as error:
        raise Exception(f"Erro ao inserir dados na tabela mov_Conhecimento_Embarque: {error}")

# Função para mapear o valor de wooden_package do PostgreSQL para o valor correspondente no SQL Server
def map_wooden_package(wooden_package):
    mapping = {
        "Treated and certified": 1,
        "NOT APPLICABLE": 2,
        "Processed": 3,
        "Do not apply": 4
    }
    return mapping.get(wooden_package, 2)  # Retorna 4 como padrão se não encontrar correspondência


# Função para mapear o kind_package para IdEquipamento_Maritimo
def map_kind_package(kind_package):
    mapping = {
        "20 TANK": 1,
        "20 PLATAFORM": 2,
        "20 DRY BOX": 3,
        "20 OPEN TOP": 4,
        "20 FLAT RACK": 5,
        "20 REEFER": 6,
        "40 PLATAFORM": 7,
        "40 FLAT RACK": 8,
        "40 HIGH CUBE": 9,
        "40 DRY BOX": 10,
        "40 OPEN TOP": 11,
        "40 REEFER": 12,
        "20 DRY S.TESTADO": 14,
        "40 DRY S.TESTADO": 15,
        "40 HC S.TESTADO": 16,
        "40 NOR": 17,
        "20 ESPECIAL (FR/PL/OT)": 18,
        "40 ESPECIAL (FR/PL/OT)": 19,
        "40 TANK": 20,
        "CARRETA": 21,
        "20 NOR": 22
    }

    # Normalizar o valor de kind_package: remover espaços e converter para maiúsculas
    kind_package_normalized = kind_package.strip().upper()

    # Retorna o valor mapeado ou None se não encontrar
    return mapping.get(kind_package_normalized, None)


# Função para separar o número de peças e o tipo de pacote
def separate_number_and_type(number_pieces):
    if number_pieces:
        parts = number_pieces.split()  # Separar por espaços
        if len(parts) >= 2:
            quantity = parts[0]  # A quantidade (por exemplo, 2500)
            type_package = " ".join(parts[1:])  # O tipo de pacote (por exemplo, CARTONS)
            return quantity, type_package
    return None, None


def insert_into_other_tables(postgre_data, next_id_conhecimento, next_id_container):
    try:
        # Conexão única
        connection = connect_to_sqlserver()
        cursor = connection.cursor()

        # Separar número de peças e tipo de pacote
        quantity, type_package = separate_number_and_type(postgre_data["number_pieces"])
        quantity = quantity or None
        type_package = type_package or None

        # Garantir conversão de valores
        try:
            gross_weight = float(re.sub(r'[^\d,\.]', '', postgre_data["gross_weight"]).replace(',', '.')) if postgre_data["gross_weight"] else None
            measurement = float(re.sub(r'[^\d,\.]', '', postgre_data["measurement"]).replace(',', '.')) if postgre_data["measurement"] else None
        except ValueError as e:
            raise ValueError(f"Erro na conversão de valores: {e}")

        # Mapear wooden_package e kind_package
        wooden_package_mapped = map_wooden_package(postgre_data["wooden_package"])
        kind_package_mapped = map_kind_package(postgre_data["kind_package"])
        if kind_package_mapped is None:
            raise ValueError(f"Não foi possível mapear kind_package: {postgre_data['kind_package']}")

        # Concatenar Description_Of_Packages
        description_of_packages = f"{quantity} - {postgre_data['description_packages']} - {wooden_package_mapped}"

        # Inserção em mov_Bill_Lading
        insert_bill_lading = """
        INSERT INTO mov_Bill_Lading (IdConhecimento_Embarque, Booking_No, Port_Of_Loading, 
                                    Port_Of_Discharge, Description_Of_Packages, Gross_Weight, 
                                    Measurement, NCM_Description, Wood_Package, Number_Of_Pieces, Bloqueado, Impresso)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        data_bill_lading = (
            next_id_conhecimento,
            postgre_data["booking"],
            postgre_data["port_loading"],
            postgre_data["port_discharge"],
            description_of_packages,
            gross_weight,
            measurement,
            postgre_data["ncm"],
            wooden_package_mapped,
            quantity,
            0,  # Bloqueado
            0   # Impresso
        )
        print(f"Executando INSERT em mov_Bill_Lading com dados: {data_bill_lading}")
        cursor.execute(insert_bill_lading, data_bill_lading)

        # Recuperar Tipo_Carga para Consolidacao
        select_tipo_carga = """
        SELECT Tipo_Carga
        FROM mov_Logistica_House
        WHERE IdLogistica_House = ?
        """
        cursor.execute(select_tipo_carga, (postgre_data["idprocesso"],))
        tipo_carga = cursor.fetchone()

        if not tipo_carga:
            raise Exception(f"Tipo_Carga não encontrado para IdLogistica_House: {postgre_data['idprocesso']}")

        # Determinar Consolidacao
        consolidacao = 1 if tipo_carga[0] == 3 else 2 if tipo_carga[0] == 4 else None
        if consolidacao is None:
            raise ValueError(f"Tipo_Carga inválido ({tipo_carga[0]}) para IdLogistica_House: {postgre_data['idprocesso']}")

        # Inserção em mov_Logistica_Maritima_Container
        insert_maritima_container = """
        INSERT INTO mov_Logistica_Maritima_Container (IdLogistica_Maritima_Container, IdConhecimento_Embarque, IdLogistica_House, 
                                                    Number, Seal, IdEquipamento_Maritimo, Quantity, Type_Packages, Tipo_Item_Carga, 
                                                    Gross_Weight, Measurement, Situacao_Devolucao, Consolidacao)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        data_maritima_container = (
            next_id_container,
            next_id_conhecimento,
            postgre_data["idprocesso"],
            postgre_data["container"],
            postgre_data["seals"],
            kind_package_mapped,
            quantity,
            type_package,
            1,  # Tipo_Item_Carga
            gross_weight,
            measurement,
            4,  # Situacao_Devolucao
            consolidacao
        )
        print(f"Executando INSERT em mov_Logistica_Maritima_Container com dados: {data_maritima_container}")
        cursor.execute(insert_maritima_container, data_maritima_container)

        # Atualizar tabelas existentes
        update_existing_tables(cursor, postgre_data)

        # Confirmar transação
        connection.commit()

    except Exception as error:
        connection.rollback()
        raise Exception(f"Erro ao inserir dados nas tabelas: {error}")

    finally:
        connection.close()

def update_existing_tables(cursor, postgre_data):
    """
    Atualiza as tabelas mov_Logistica_House e mov_Logistica_Maritima_House.
    """
    idlogistica_house = postgre_data["idprocesso"]
    bill_no = postgre_data["bill_no"]
    container = postgre_data["container"]

    # Atualizar a coluna Conhecimentos na tabela mov_Logistica_House
    update_lhs = """
    UPDATE mov_Logistica_House
    SET Conhecimentos = ?
    WHERE IdLogistica_House = ?
    """
    print(f"Atualizando mov_Logistica_House com Conhecimentos: {bill_no}, IdLogistica_House: {idlogistica_house}")
    cursor.execute(update_lhs, (bill_no, idlogistica_house))

    # Atualizar a tabela mov_Logistica_Maritima_House
    update_maritima_house = """
    UPDATE mov_Logistica_Maritima_House
    SET Containers = ?
    WHERE IdLogistica_House = ?
    """
    print(f"Atualizando mov_Logistica_Maritima_House com Containers: {container}, IdLogistica_House: {idlogistica_house}")
    cursor.execute(update_maritima_house, (container, idlogistica_house))


# Função principal para integrar todo o fluxo
def main_integration(postgre_data):
    try:
        # 1. Realize o select no SQL Server para obter os dados necessários
        sql_data = get_sql_data(postgre_data["idprocesso"])

        # 2. Obter o maior ID atual na tabela mov_Conhecimento_Embarque
        max_id_conhecimento = get_max_id_from_table("mov_Conhecimento_Embarque", "IdConhecimento_Embarque")
        next_id_conhecimento = generate_sequential_id(max_id_conhecimento, 'mov_Conhecimento_Embarque')

        # 3. Insira na tabela mov_Conhecimento_Embarque
        insert_into_conhecimento_embarque(postgre_data, sql_data, next_id_conhecimento)

        # 4. Obter o maior ID atual na tabela mov_Logistica_Maritima_Container
        max_id_container = get_max_id_from_table("mov_Logistica_Maritima_Container", "IdLogistica_Maritima_Container")
        next_id_container = generate_sequential_id(max_id_container, 'mov_Logistica_Maritima_Container')

        # 5. Insira nas tabelas mov_Bill_Lading e mov_Logistica_Maritima_Container
        insert_into_other_tables(postgre_data, next_id_conhecimento, next_id_container)

        # Retorne o next_id_conhecimento para ser usado posteriormente
        return next_id_conhecimento

    except Exception as e:
        raise Exception(f"Erro no processo de integração: {e}")