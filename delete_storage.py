import requests

# Configuração do token de autorização para a API
TOKEN = "eyJhbGciOiJodHRwOi8vd3d3LnczLm9yZy8yMDAxLzA0L3htbGRzaWctbW9yZSNobWFjLXNoYTI1NiIsInR5cCI6IkpXVCJ9.eyJodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9uYW1laWRlbnRpZmllciI6IjU4YjVmNWU3LTgyYTItNDEyMS05ODM2LWY3YzliZmQ3NjM4YSIsImNvbnRhaW5lciI6ImtwbSIsImlzcyI6IkhlYWRTb2Z0IiwiYXVkIjoiRmlsZVN0cmVhbSJ9.BldzJwg8hP9eT7IiZoAE6eB7UbKoyVge9mx1fawHnVU"

# Função para excluir o arquivo no storage usando o hash
def delete_file_from_storage(hash_value):
    # Verificar se o arquivo com o hash existe no storage
    headers = {"Authorization": f"Bearer {TOKEN}"}
    check_url = f"https://api.headsoft.com.br/geral/blob-stream/private/find?hash={hash_value}"
    check_response = requests.get(check_url, headers=headers)

    # Se o arquivo existir no storage
    if check_response.status_code == 200 and check_response.json().get("id"):
        # Obtém o GUID do arquivo
        guid = check_response.json()["id"][0]
        
        # URL para exclusão do arquivo no storage
        delete_url = f"https://api.headsoft.com.br/geral/blob-stream/private/{guid}"
        
        # Realizar a exclusão
        delete_response = requests.delete(delete_url, headers=headers)
        
        if delete_response.status_code == 200:
            print(f"Arquivo com GUID {guid} excluído com sucesso do storage.")
        else:
            print(f"Erro ao excluir o arquivo. Status: {delete_response.status_code}")
    else:
        print("Arquivo não encontrado no storage ou já excluído.")

# Exemplo de uso
file_hash = "d0810fcb-b1d0-4e47-9fb6-af7a37cad051', 'd38484aa-ef2e-4038-8049-bbb6b9007024', 'f5882712-233b-4df8-85e2-16cc255c7751', 'f6f68b0e-3c82-46b9-86b5-03792dbf82c7"
delete_file_from_storage(file_hash)
