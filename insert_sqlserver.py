import pyodbc
from datetime import datetime
import re

# Função para conectar ao SQL Server
def connect_to_sqlserver():
    try:
        connection = pyodbc.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};'
            'SERVER=kpm.sql.headcargo.com.br,9322;'
            'DATABASE=HeadCARGO_KPM_HOMOLOGACAO;'
            'UID=hc_kpm_ti;'
            'PWD=971639DA-D739-4C0F-83D5-6E34037092FD'
        )
        return connection
    except Exception as error:
        raise Exception(f"Erro ao conectar ao SQL Server: {error}")

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
        connection = connect_to_sqlserver()
        cursor = connection.cursor()

        # Separar o número de peças e o tipo de pacote
        quantity, type_package = separate_number_and_type(postgre_data["number_pieces"])

        # Se os valores não forem válidos, define como None
        if not quantity:
            quantity = None
        if not type_package:
            type_package = None

        # Garantir que os campos gross_weight e measurement sejam convertidos corretamente para float
        try:
            # Remove todas as letras e espaços extras antes de converter para float
            gross_weight_cleaned = re.sub(r'[^\d,.]', '', postgre_data["gross_weight"]) if postgre_data["gross_weight"] else None
            gross_weight = float(gross_weight_cleaned.replace(".", "").replace(",", ".")) if gross_weight_cleaned else None
        except ValueError:
            raise Exception(f"Erro ao converter 'gross_weight': {postgre_data['gross_weight']}")

        try:
            # Remove todas as letras e espaços extras antes de converter para float
            measurement_cleaned = re.sub(r'[^\d,.]', '', postgre_data["measurement"]) if postgre_data["measurement"] else None
            measurement = float(measurement_cleaned.replace(",", ".")) if measurement_cleaned else None
        except ValueError:
            raise Exception(f"Erro ao converter 'measurement': {postgre_data['measurement']}")
        
        # Converter o valor de wooden_package e kind_package
        wooden_package_mapped = map_wooden_package(postgre_data["wooden_package"])
        kind_package_mapped = map_kind_package(postgre_data["kind_package"])

        if kind_package_mapped is None:
            raise Exception(f"Não foi possível mapear o kind_package: {postgre_data['kind_package']}")

        # Inserção na tabela mov_Bill_Lading
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
            postgre_data["description_packages"],
            gross_weight,  # Usar valor numérico convertido
            measurement,   # Usar valor numérico convertido
            postgre_data["ncm"],
            wooden_package_mapped,  # Valor mapeado para Wood_Package
            quantity,  # Apenas a quantidade vai para Number_Of_Pieces
            0,  # Valor fixo para Bloqueado
            0   # Valor fixo para Impresso
        )

        cursor.execute(insert_bill_lading, data_bill_lading)

        # Inserção na tabela mov_Logistica_Maritima_Container
        insert_maritima_container = """
        INSERT INTO mov_Logistica_Maritima_Container (IdLogistica_Maritima_Container, IdConhecimento_Embarque, IdLogistica_House, 
                                                    Number, Seal, IdEquipamento_Maritimo, Quantity, Type_Packages, Tipo_Item_Carga, Gross_Weight, Measurement)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            1,  
            gross_weight,  
            measurement
        )
        cursor.execute(insert_maritima_container, data_maritima_container)

        connection.commit()
        connection.close()

    except Exception as error:
        raise Exception(f"Erro ao inserir dados nas tabelas mov_Bill_Lading ou mov_Logistica_Maritima_Container: {error}")


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