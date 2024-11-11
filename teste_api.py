from dotenv import load_dotenv
import os

# Caminho absoluto para o arquivo .env
env_path = 'C:/Pedro/Python/bl_spacy/.env'
load_dotenv(env_path)

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

if GOOGLE_API_KEY:
    print(f"Chave da API encontrada: {GOOGLE_API_KEY}")
else:
    print("Chave da API NÃO encontrada.")
