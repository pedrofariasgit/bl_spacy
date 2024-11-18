from datetime import datetime
import streamlit as st
import pyodbc
import os

def get_process_data(numero_processo):
    query = f"""
    SELECT top 1
        Ori.Nome AS port_loading, 
        Dst.Nome AS port_discharge,
        Dfi.Nome AS final_delivery,
        Mem.Descricao as kind_package,
        Mer.Nome as description_packages,
        Lhs.IdLogistica_House as idprocesso,
        Lms.IdCompanhia_Transporte as idcia
    FROM
        mov_Logistica_House Lhs
    LEFT OUTER JOIN
		mov_Logistica_Master Lms ON Lms.IdLogistica_Master = Lhs.IdLogistica_Master
    LEFT OUTER JOIN
        mov_Logistica_Viagem Lgo ON Lgo.IdLogistica_House = Lhs.IdLogistica_House AND Lgo.Tipo_Viagem = 4
    LEFT OUTER JOIN
        mov_Logistica_Viagem Lfi ON Lfi.IdLogistica_House = Lhs.IdLogistica_House AND Lfi.Tipo_Viagem = 8
    LEFT OUTER JOIN
        (
        SELECT 
            IdLogistica_House, 
            IdDestino,
            MAX(Data_Previsao_Desembarque) AS Ultimo_prev_desembarque
        FROM 
            mov_Logistica_Viagem
        GROUP BY 
            IdLogistica_House, IdDestino 
        ) Lgd ON Lgd.IdLogistica_House = Lhs.IdLogistica_House
    LEFT OUTER JOIN
        cad_Origem_Destino Ori ON Ori.IdOrigem_Destino = Lgo.IdOrigem
    LEFT OUTER JOIN
        cad_Origem_Destino Dst ON Dst.IdOrigem_Destino = Lgd.IdDestino
    LEFT OUTER JOIN
        cad_Origem_Destino Dfi ON Dfi.IdOrigem_Destino = Lfi.IdDestino
    LEFT OUTER JOIN
        mov_Logistica_Maritima_Equipamento Lme on Lme.IdLogistica_House = Lhs.IdLogistica_House
    LEFT OUTER JOIN
        cad_Equipamento_Maritimo Mem on Mem.IdEquipamento_Maritimo = Lme.IdEquipamento_Maritimo
    LEFT OUTER JOIN
        cad_Mercadoria Mer on Mer.IdMercadoria = Lhs.IdMercadoria
    WHERE
        Lhs.Numero_Processo = '{numero_processo}'
    """
    try:
        connection = pyodbc.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};'
            f"SERVER={os.getenv('SQLSERVER_HOST')};"
            f"DATABASE={os.getenv('SQLSERVER_DATABASE')};"
            f"UID={os.getenv('SQLSERVER_USER')};"
            f"PWD={os.getenv('SQLSERVER_PASSWORD')};"
        )
        cursor = connection.cursor()
        cursor.execute(query)
        result = cursor.fetchone()
        connection.close()

        # Aqui, 'idprocesso' deve ser parte do resultado
        if result:
            return {
                "port_loading": result.port_loading if result.port_loading else "",
                "port_discharge": result.port_discharge if result.port_discharge else "",
                "final_delivery": result.final_delivery if result.final_delivery else "",
                "kind_package": result.kind_package if result.kind_package else "",
                "description_packages": result.description_packages if result.description_packages else "",
                "idcia": result.idcia if result.idcia else "",
                "idprocesso": result.idprocesso if result.idprocesso else None  # Garantir que 'idprocesso' seja retornado
            }
        else:
            return None
    except Exception as e:
        st.error(f"Erro ao consultar o banco de dados: {e}")
        return None