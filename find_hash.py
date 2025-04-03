import hashlib

# Função para calcular o SHA-512 do arquivo
def calculate_file_hash_sha512(file_path):
    sha512_hash = hashlib.sha512()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha512_hash.update(byte_block)
        return sha512_hash.hexdigest()
    except FileNotFoundError:
        print("Arquivo não encontrado. Verifique o caminho e tente novamente.")
        return None

# Caminho do arquivo para cálculo do hash
file_path = r"C:\Users\kpm_t\OneDrive\Área de Trabalho\Area de Trabalho\Grau de risco - Decreto nº 11.985 2020.pdf"

# Calcular e exibir o hash no terminal
file_hash = calculate_file_hash_sha512(file_path)
if file_hash:
    print("O hash SHA-512 do arquivo é:", file_hash)

