# ia_draft_to_erp

Este projeto automatiza o processamento de drafts utilizando Inteligência Artificial (Gemini), transforma os dados extraídos em JSON estruturado, armazena em um banco PostgreSQL e realiza a integração com o ERP via SQL Server.

---

## 🔄 Fluxo de Funcionamento

1. **Upload do draft (PDF ou texto)**
2. **Leitura e extração dos campos via IA (Gemini API)**
3. **Estruturação dos dados em formato JSON**
4. **Inserção no banco de dados PostgreSQL**
5. **Envio das informações estruturadas para o ERP (SQL Server)**

---

## 📂 Estrutura do projeto

- `main.py`: Orquestra o processo completo: leitura, extração, inserção no PostgreSQL e envio ao ERP.
- `extract_gemini.py`: Responsável por enviar o draft à IA e retornar os dados estruturados.
- `insert_postgre.py`: Realiza o insert no banco de dados PostgreSQL.
- `insert_sqlserver.py`: Realiza o insert no ERP (SQL Server).
- `.env`: Armazena variáveis sensíveis como chaves de API e dados de conexão (não incluso no GitHub).

---

## 🧠 Exemplo de saída JSON da IA

```json
{
  "booking": "NGP1234567",
  "port_loading": "Santos",
  "port_discharge": "Rotterdam",
  "container": "AAAU1234567",
  "gross_weight": "15200 KG",
  "packages": "1 X 40HC",
  ...
}