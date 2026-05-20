"""Teste de inserção de produto pela área administrativa."""


def test_novo_produto_admin_sucesso(client):
    with client.session_transaction() as sess:
        sess["vendedor_logado"] = True
        sess["is_admin"] = True
        sess["vendedor_email"] = "giovanna.markxs@gmail.com"
        sess["vendedor_id"] = 1
        sess["vendedor_nome"] = "Administradora"

    response = client.post(
        "/vendedor/produto/novo",
        json={
            "nome": "Novo Produto",
            "descricao": "Descrição teste",
            "categoria_id": 1,
            "preco": 99.9,
            "estoque": 5,
            "imagem": "",
        },
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
