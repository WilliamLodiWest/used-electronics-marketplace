import os
import sys

import pytest
from flask import Flask
from jinja2 import ChoiceLoader, DictLoader
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROUTES_DIR = os.path.join(BASE_DIR, "routes")

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if ROUTES_DIR not in sys.path:
    sys.path.insert(0, ROUTES_DIR)

import produto as produto_mod
import produtos_suporte as suporte_mod
import vendedor as vendedor_mod
import administrador as admin_mod


class FakeConexaoBD:
    def __init__(self):
        self._cliente_hash = generate_password_hash("123456", method="pbkdf2:sha256")

    def select(self, sql, params=None):
        query = " ".join(str(sql).lower().split())
        params = params or ()

        if "from clientes_tt where email = %s" in query and "id_cliente, nome, senha" in query:
            if params and params[0] == "teste@email.com":
                return [(1, "Cliente Teste", self._cliente_hash)]
            return []

        if "from clientes_tt where email = %s" in query and "id_cliente, nome" in query:
            if params and params[0] == "teste@email.com":
                return [(1, "Cliente Teste")]
            return []

        if "from categorias_produtos_tt" in query and "where id_categoria = %s" in query:
            return [(1,)]

        if "from categorias_produtos_tt" in query:
            return [(1, "Celulares")]

        if "from vendedores_tt where email = %s" in query:
            return [(1,)]

        if "insert into vendedores_tt" in query:
            return 1

        if "from produtos_tt p left join categorias_produtos_tt" in query:
            return [
                (
                    1,
                    "Produto Teste",
                    "Descricao",
                    "Celulares",
                    99.9,
                    10,
                    None,
                    "Admin",
                    None,
                    1,
                    "Admin",
                    None,
                    "",
                )
            ]

        if "from produtos_tt p where p.id_produto = %s" in query and "p.descricao" in query:
            if params and int(params[0]) == 1:
                return [(1, "Produto Teste", "Descricao", 99.9, 10, None, 1, "Admin", 1)]
            return []

        if "from produtos_tt where id_produto = %s" in query and "nome, descricao, preco" in query:
            if params and int(params[0]) == 1:
                return [("Produto Teste", "Descricao", 99.9, "Admin", "")]
            return []

        if "from produtos_tt p left join vendedores_tt v" in query:
            if params and int(params[0]) == 1:
                return [(99.9, 10, 1, "Produto Teste", "Admin", 1, None)]
            return []

        if "from compras_tt where codigo_rastreio = %s" in query:
            return []

        if "information_schema.columns" in query.lower():
            p = params or ()
            if len(p) == 2 and p[0] == "produtos_tt" and p[1] == "chave_nfe":
                return []
            if len(p) == 2 and p[0] == "compras_tt" and p[1] == "codigo_rastreio":
                return []
            if len(p) == 2 and p[0] == "compras_tt" and p[1] == "status":
                return [("enum('pendente','processando','enviado','entregue','cancelado')",)]
            return []

        if "count(*) as total_produtos" in query:
            return [(2, 25)]

        if "count(*) as total_vendas" in query and "receita_total" in query:
            return [(3, 500.0)]

        if "from notificacoes_tt" in query and "count(*)" in query:
            return [(1,)]

        if "from compras_tt c join produtos_tt p" in query and "limit 10" in query:
            return []

        if "from produtos_tt" in query and "estoque < 10" in query:
            return []

        if "from produtos_tt p left join categorias_produtos_tt c" in query and "where p.criado_por_id = %s" in query:
            return [(1, "Produto Teste", "Descricao", 1, 99.9, 10, None, 1, "Celulares")]

        if "from notificacoes_tt" in query and "limit 50" in query:
            return []

        if "from produtos_tt where id_produto = %s and criado_por_id = %s" in query:
            return [(1,)]

        if "from compras_tt where id_produto = %s and status != 'cancelado'" in query:
            return []

        if "from compras_tt c join produtos_tt p join clientes_tt cl" in query and "where c.id_compra = %s" in query:
            return [(1, "Produto Teste", "Cliente", "cliente@email.com")]

        return []

    def insert(self, sql, params=None):
        return 1

    def update(self, sql, params=None):
        return 1

    def delete(self, sql, params=None):
        return 1

    def close(self):
        return None


@pytest.fixture(autouse=True)
def mock_bd(monkeypatch):
    monkeypatch.setattr(produto_mod, "ConexaoBD", FakeConexaoBD)
    monkeypatch.setattr(suporte_mod, "ConexaoBD", FakeConexaoBD)
    monkeypatch.setattr(vendedor_mod, "ConexaoBD", FakeConexaoBD)
    monkeypatch.setattr(admin_mod, "ConexaoBD", FakeConexaoBD)


@pytest.fixture
def app():
    template_dir = os.path.join(BASE_DIR, "templates")
    static_dir = os.path.join(BASE_DIR, "static")
    flask_app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    flask_app.secret_key = "teste"
    flask_app.config["TESTING"] = True
    flask_app.jinja_loader = ChoiceLoader(
        [
            flask_app.jinja_loader,
            DictLoader(
                {
                    # Template utilizado por rota existente, mas ausente no projeto.
                    "comprovante.html": "<html><body>Comprovante</body></html>",
                    "vendedor_cadastro.html": "<html><body>Cadastro vendedor</body></html>",
                }
            ),
        ]
    )
    flask_app.register_blueprint(produto_mod.rotas_produto)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()