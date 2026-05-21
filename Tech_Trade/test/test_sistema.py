import pytest

import produto as produto_mod
import vendedor as vendedor_mod
from src.utils.schema_compat import (
    TAG_AGUARDA_APROVACAO,
    limpar_tag_aprovacao_obs,
    pedido_aguarda_aprovacao_admin,
)


# -----------------------------
# TESTES UNITARIOS
# -----------------------------

@pytest.mark.parametrize(
    ("nome", "esperado"),
    [
        ("Joao Silva", "JS"),
        ("ana", "AN"),
        ("", ""),
        (None, ""),
    ],
)
def test_unit_iniciais_nome(nome, esperado):
    assert produto_mod._iniciais_nome(nome) == esperado


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        (None, None),
        ("", None),
        ("foto.png", "foto.png"),
        ("/tech_trade_imagens/foto.png", "foto.png"),
        ("https://cdn.site/imagem.jpg", "https://cdn.site/imagem.jpg"),
    ],
)
def test_unit_normalizar_imagem(entrada, esperado):
    assert vendedor_mod._normalizar_imagem_produto(entrada) == esperado


def test_unit_montar_url_imagem_local():
    assert vendedor_mod._montar_url_imagem_produto("teste.png") == "/static/tech_trade_imagens/teste.png"


def test_unit_montar_url_imagem_fallback():
    assert vendedor_mod._montar_url_imagem_produto(None) == "/static/img/sem-imagem.png"


# -----------------------------
# TESTES DE INTEGRACAO
# -----------------------------

@pytest.mark.parametrize(
    "rota",
    [
        "/",
        "/login",
        "/cadastro",
        "/produtos",
        "/suporte_comprador",
        "/vendedor/login",
        "/esqueceu_senha",
    ],
)
def test_paginas_publicas_disponiveis(client, rota):
    response = client.get(rota)
    assert response.status_code == 200


def test_login_cliente_sucesso_redireciona_produtos(client):
    response = client.post(
        "/login",
        data={"email": "teste@email.com", "senha": "123456"},
    )
    assert response.status_code == 302
    assert "/produtos" in response.location


def test_logout_limpa_sessao(client):
    with client.session_transaction() as sess:
        sess["usuario_logado"] = True
        sess["usuario_nome"] = "Teste"
    client.get("/logout")
    with client.session_transaction() as sess:
        assert "usuario_logado" not in sess
        assert "usuario_nome" not in sess


def test_esqueceu_senha_sem_email(client):
    response = client.post("/esqueceu_senha", data={})
    assert response.status_code == 400
    assert response.get_json()["erro"] == "Por favor, informe seu e-mail."


def test_esqueceu_senha_com_email_valido(client):
    response = client.post("/esqueceu_senha", data={"email": "teste@email.com"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "message" in data
    assert "link" in data


def test_rota_verificar_produto_sem_admin(client):
    response = client.post("/techtrade/produtos/verificar", json={"id_produto": 1})
    assert response.status_code == 403
    assert response.get_json()["erro"] == "Acesso restrito à administradora."


def test_rota_verificar_produto_com_admin_sem_id(client):
    with client.session_transaction() as sess:
        sess["is_admin"] = True
    response = client.post("/techtrade/produtos/verificar", json={})
    assert response.status_code == 400
    assert response.get_json()["erro"] == "ID do produto é obrigatório"


def test_rota_verificar_produto_com_admin_sucesso(client):
    with client.session_transaction() as sess:
        sess["is_admin"] = True
    response = client.post("/techtrade/produtos/verificar", json={"id_produto": 1})
    assert response.status_code == 200
    assert response.get_json()["mensagem"] == "Produto verificado com sucesso!"


def test_consultar_categorias(client):
    response = client.get("/techtrade/categorias")
    assert response.status_code == 200
    assert isinstance(response.get_json(), list)
    

def test_consultar_produtos(client):
    response = client.get("/techtrade/produtos/registros")
    assert response.status_code == 200
    assert "json_produtos" in response.get_json()


def test_checkout_produto_existente(client):
    response = client.get("/techtrade/produtos/checkout/1")
    assert response.status_code == 200


def test_comprovante_produto_existente(client):
    response = client.get("/comprovante/1")
    assert response.status_code == 200


def test_finalizar_compra_sem_login(client):
    response = client.post("/techtrade/produtos/finalizar_compra_completa", json={})
    assert response.status_code == 401
    assert response.get_json()["erro"] == "Usuário não logado"


def test_finalizar_compra_com_login(client):
    with client.session_transaction() as sess:
        sess["usuario_logado"] = True
        sess["usuario_id"] = 1
        sess["usuario_nome"] = "Cliente Teste"
    response = client.post(
        "/techtrade/produtos/finalizar_compra_completa",
        json={"id_produto": 1, "metodo_pagamento": "PIX", "endereco_entrega": "Rua A"},
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["mensagem"] == "Pedido registrado! Aguarde aprovação da administradora."
    assert "codigo_rastreio" in data


def test_confirmacao_sem_produto_redireciona(client):
    response = client.get("/confirmacao")
    assert response.status_code == 302
    assert "/produtos" in response.location


def test_confirmacao_com_produto_na_sessao(client):
    with client.session_transaction() as sess:
        sess["produto"] = {"id_produto": 1, "nome": "Produto Teste", "preco": 99.9}
        sess["metodo"] = "PIX"
        sess["mensagem"] = "Compra realizada com sucesso!"
        sess["usuario_nome"] = "Cliente Teste"
    response = client.get("/confirmacao")
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("metodo", "rota"),
    [
        ("get", "/vendedor/dashboard"),
        ("get", "/vendedor/api/dashboard"),
        ("get", "/vendedor/api/produtos"),
        ("get", "/vendedor/api/notificacoes"),
        ("post", "/vendedor/api/notificacoes/marcar_lida"),
        ("post", "/vendedor/api/notificacoes/marcar_todas_lidas"),
        ("post", "/vendedor/api/notificacoes/excluir"),
        ("post", "/vendedor/produto/novo"),
        ("put", "/vendedor/produto/editar/1"),
        ("delete", "/vendedor/produto/deletar/1"),
        ("get", "/vendedor/pedidos/json"),
        ("post", "/vendedor/pedidos/atualizar_status/1"),
        ("post", "/vendedor/pedidos/aprovar/1"),
        ("post", "/vendedor/pedidos/reprovar/1"),
    ],
)
def test_rotas_vendedor_bloqueadas_sem_login(client, metodo, rota):
    response = getattr(client, metodo)(rota)
    if rota == "/vendedor/dashboard":
        assert response.status_code == 302
    else:
        assert response.status_code == 401
        assert response.get_json()["erro"] == "Não autorizado"


def test_login_vendedor_admin_redireciona_dashboard(client):
    response = client.post(
        "/vendedor/login",
        data={"email": "giovanna.markxs@gmail.com", "senha": "1234"},
    )
    assert response.status_code == 302
    assert "/vendedor/dashboard" in response.location


def test_vendedor_dashboard_autenticado(client):
    with client.session_transaction() as sess:
        sess["vendedor_logado"] = True
        sess["is_admin"] = True
        sess["vendedor_email"] = "giovanna.markxs@gmail.com"
        sess["vendedor_id"] = 1
        sess["vendedor_nome"] = "Administradora"
    response = client.get("/vendedor/dashboard")
    assert response.status_code == 200


def test_vendedor_logout(client):
    with client.session_transaction() as sess:
        sess["vendedor_logado"] = True
        sess["is_admin"] = True
        sess["vendedor_email"] = "giovanna.markxs@gmail.com"
        sess["vendedor_id"] = 1
        sess["vendedor_nome"] = "Administradora"
    response = client.get("/vendedor/logout")
    assert response.status_code == 302


# -----------------------------
# COBERTURA EM CADA ROTA
# -----------------------------

def _substituir_args_rota(rule):
    path = rule.rule
    for argumento in rule.arguments:
        path = path.replace(f"<int:{argumento}>", "1")
        path = path.replace(f"<{argumento}>", "token-teste")
    return path


def _metodo_principal(rule):
    for metodo in ("GET", "POST", "PUT", "DELETE", "PATCH"):
        if metodo in rule.methods:
            return metodo
    return "GET"


def _rules_produto(app):
    return sorted(
        [r for r in app.url_map.iter_rules() if r.endpoint.startswith("produto.")],
        key=lambda r: (r.rule, r.endpoint),
    )


def test_integracao_cada_rota_registrada(app, client):
    """Garante que toda rota responde sem erro interno."""
    for rule in _rules_produto(app):
        method = _metodo_principal(rule)
        path = _substituir_args_rota(rule)
        kwargs = {"method": method}
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            kwargs["data"] = {}

        response = client.open(path, **kwargs)
        assert response.status_code < 500, f"Falha em {method} {path} ({rule.endpoint})"


@pytest.mark.parametrize(
    ("status", "obs", "codigo", "esperado"),
    [
        ("aguardando_aprovacao", "", "", True),
        ("pendente", f"{TAG_AGUARDA_APROVACAO}|COD:TT-ABC123|", "", True),
        ("pendente", "", "TT-XYZ", True),
        ("processando", f"{TAG_AGUARDA_APROVACAO}|COD:TT-ABC123|", "TT-ABC123", False),
        ("pago", "", "TT-ABC123", False),
        ("entregue", "", "TT-ABC123", False),
    ],
)
def test_pedido_aguarda_aprovacao_admin(status, obs, codigo, esperado):
    assert pedido_aguarda_aprovacao_admin(status, obs, codigo) is esperado


def test_limpar_tag_aprovacao_obs():
    obs = f"{TAG_AGUARDA_APROVACAO}|COD:TT-1|\nObservação do cliente"
    assert limpar_tag_aprovacao_obs(obs) == "Observação do cliente"


def test_unitario_cada_view_de_rota(app):
    """
    Chama diretamente cada função de rota em request context.
    Isto valida a view (unidade) sem passar pelo roteador HTTP.
    """
    for rule in _rules_produto(app):
        method = _metodo_principal(rule)
        path = _substituir_args_rota(rule)
        view_func = app.view_functions[rule.endpoint]
        view_kwargs = {argumento: (1 if "int:" in rule.rule else "token-teste") for argumento in rule.arguments}

        context_kwargs = {"method": method}
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            context_kwargs["data"] = {}

        with app.test_request_context(path, **context_kwargs):
            retorno = view_func(**view_kwargs)
            response = app.make_response(retorno)
            assert response.status_code < 500, f"Erro interno na view {rule.endpoint}"