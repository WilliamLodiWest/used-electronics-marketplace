# Tech-Trade
PIM

## Deploy no Render

O app é **Flask** com **MySQL** — use um **Web Service** no [Render](https://render.com/), não site estático.

### 1. Banco MySQL na nuvem

Crie um MySQL (Render PostgreSQL não serve; use por exemplo [Aiven](https://aiven.io/), [PlanetScale](https://planetscale.com/) ou MySQL em outro provedor). Execute os scripts em `migrations/` no banco.

### 2. Web Service no Render

1. **New** → **Web Service** → conecte o repositório `Projeto-Extensao`.
2. Branch: `main` ou `feature/ajustes`.
3. Configuração:

| Campo | Valor |
|--------|--------|
| **Root Directory** | `Tech_Trade` |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn wsgi:app --bind 0.0.0.0:$PORT` |

4. **Environment** (obrigatório para o site funcionar):

| Variável | Exemplo |
|----------|---------|
| `SECRET_KEY` | string longa aleatória (Render pode gerar) |
| `DB_HOST` | host do MySQL na nuvem |
| `DB_PORT` | `3306` (ou a porta do provedor) |
| `DB_USER` | usuário do banco |
| `DB_PASSWORD` | senha |
| `DB_NAME` | `tech_trade_db` |
| `DB_SSL` | `true` se o provedor exigir SSL |
| `OPENAI_API_KEY` | opcional — chat com IA |

5. **Deploy**. A URL será algo como `https://tech-trade-xxxx.onrender.com`.

Alternativa: importar o blueprint `render.yaml` (pasta `Tech_Trade`) em **New** → **Blueprint**.

### 3. Testar localmente como produção

```powershell
cd Tech_Trade
pip install -r requirements.txt
$env:SECRET_KEY = "teste-local"
$env:DB_HOST = "127.0.0.1"
$env:DB_USER = "root"
$env:DB_PASSWORD = "sua_senha"
$env:DB_NAME = "tech_trade_db"
gunicorn wsgi:app --bind 127.0.0.1:8000
```

Abra `http://127.0.0.1:8000`.

---

## Usando MySQL (MySQL Workbench)

Este projeto por padrão usa SQLite local (`tech_trade.db`) quando não há variáveis de ambiente de conexão com MySQL.

Se você prefere usar MySQL (por exemplo MySQL Workbench), siga estes passos:

1. Abra o MySQL Workbench e conecte ao seu servidor MySQL.
2. No menu de query, abra e execute o arquivo `sql/schema.sql` para criar o database `tech_trade` e a tabela `produto`.
3. Ainda no Workbench, execute `sql/seed.sql` para inserir dados de exemplo.

Variáveis de ambiente (opcionais). Se definidas, o app tentará usar MySQL ao invés de SQLite:

- MYSQL_HOST (ex: 127.0.0.1)
- MYSQL_PORT (padrão: 3306)
- MYSQL_USER
- MYSQL_PASSWORD
- MYSQL_DB (padrão sugerido no schema: tech_trade)

Exemplo (Windows PowerShell):

```powershell
$env:MYSQL_HOST = '127.0.0.1'; $env:MYSQL_USER = 'root'; $env:MYSQL_PASSWORD = 'senha'; $env:MYSQL_DB = 'tech_trade'
python produto.py
```

Depois de configurar e importar o schema/seed, a rota `/registros_sgs/produtos` vai buscar os dados diretamente do banco MySQL.

Observação: se `mysql-connector-python` não estiver instalado, instale com:

```powershell
pip install mysql-connector-python
```

