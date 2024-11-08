import psycopg2
from datetime import datetime
import re
import os

# Função para normalizar números (remove vírgulas e pontos desnecessários)
def normalize_number(number_str):
    if number_str:
        # Remove qualquer caractere que não seja número, ponto ou vírgula
        cleaned_number = re.sub(r'[^\d,.]', '', number_str)
        # Remove o ponto que separa milhar e substitui a vírgula por ponto para número decimal
        cleaned_number = cleaned_number.replace(".", "").replace(",", ".")
        return float(cleaned_number)
    return None

def insert_data_postgre(bill_no, booking, container_input, seals_input, number_pieces, gross_weight, measurement, ncm, wooden_package,
                        port_loading, port_discharge, final_place, kind_package, description_packages,
                        numero_processo_input, idcia, idprocesso):
    try:
        # Conectar ao banco de dados PostgreSQL
        connection = psycopg2.connect(
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT"),
            database=os.getenv("POSTGRES_DATABASE")
        )
        cursor = connection.cursor()

        # Certificar que campos em branco são tratados
        number_pieces = number_pieces if number_pieces else None  
        gross_weight = normalize_number(gross_weight)
        measurement = normalize_number(measurement)

        # Query de inserção
        insert_query = """
        INSERT INTO pdf_info (bill_no, booking, container, seals, number_pieces, gross_weight, measurement, ncm, wooden_package, 
                              port_loading, port_discharge, final_place, kind_package, description_packages, 
                              numero_processo, idcia, idprocesso, upload_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        data = (
            bill_no, booking, container_input, seals_input, number_pieces, gross_weight, measurement, ncm, wooden_package, 
            port_loading, port_discharge, final_place, kind_package, description_packages, 
            numero_processo_input, idcia, idprocesso, datetime.now()
        )

        # Executar o comando de inserção
        cursor.execute(insert_query, data)
        connection.commit()

        # Fechar conexão
        cursor.close()
        connection.close()

    except Exception as error:
        raise Exception(f"Erro ao inserir dados no PostgreSQL: {error}")