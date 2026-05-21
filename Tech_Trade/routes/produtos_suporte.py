import re
import secrets
from datetime import datetime
from flask import abort, jsonify, redirect, render_template, request, session, url_for
from src.utils.bd import ConexaoBD
from src.utils.schema_compat import (
    compras_status_enum_values,
    embutir_codigo_em_observacoes,
    extrair_codigo_rastreio_obs,
    table_has_column,
)

# Portal oficial de consulta de NF-e (usuário informa a chave de 44 dígitos no site da Receita).
URL_CONSULTA_NFE = "https://www.nfe.fazenda.gov.br/portal/consultaRecaptcha.aspx?tipoConsulta=completa"


def _gerar_codigo_rastreio():
    return "TT-" + secrets.token_hex(5).upper()


def _notificar_vendedores(conexao, ids_vendedor, mensagem):
    """Envia a mesma notificação para uma lista de id_vendedor (sem duplicar None)."""
    sql_notificacao = """
        INSERT INTO notificacoes_tt (id_vendedor, mensagem, data_envio, lida)
        VALUES (%s, %s, NOW(), 0)
    """
    vistos = set()
    for vid in ids_vendedor:
        if vid is None or vid in vistos:
            continue
        vistos.add(vid)
        conexao.insert(sql_notificacao, (vid, mensagem))

try:
    from .produto import rotas_produto
except ImportError:
    from produto import rotas_produto


@rotas_produto.route("/produtos")
def renderizar_produtos():
    try:
        return render_template("produtos.html")
    except Exception:
        abort(404)


@rotas_produto.get("/techtrade/categorias")
def consultar_categorias_produtos():
    try:
        conexao = ConexaoBD()
        categorias = conexao.select("SELECT id_categoria, nome FROM categorias_produtos_tt")
        conexao.close()
        return jsonify(categorias)
    except Exception as err:
        return jsonify({"erro": str(err).replace("'", '"')}), 500


@rotas_produto.get("/techtrade/produtos/registros")
def consultar_produtos():
    try:
        conexao_bd = ConexaoBD()
        has_chave_nfe = table_has_column(conexao_bd, "produtos_tt", "chave_nfe")
        sql_base = """
            SELECT
                p.id_produto,
                p.nome,
                p.descricao,
                c.nome AS categoria,
                p.preco,
                p.estoque,
                p.criado_em,
                p.criado_por,
                p.imagem,
                p.verificado,
                p.verificado,
                p.verificado_em
        """
        if has_chave_nfe:
            sql = sql_base + ", p.chave_nfe FROM produtos_tt p LEFT JOIN categorias_produtos_tt c ON p.categoria_id = c.id_categoria ORDER BY p.id_produto DESC"
        else:
            sql = sql_base + " FROM produtos_tt p LEFT JOIN categorias_produtos_tt c ON p.categoria_id = c.id_categoria ORDER BY p.id_produto DESC"
        retorno_bd = conexao_bd.select(sql)
        conexao_bd.close()

        def formata_data(data):
            if isinstance(data, datetime):
                return data.strftime('%d/%m/%Y')
            return str(data) if data else ""

        def safe_float(valor):
            try:
                return float(valor) if valor is not None else 0.0
            except (TypeError, ValueError):
                return 0.0

        def safe_int(valor):
            try:
                return int(valor) if valor is not None else 0
            except (TypeError, ValueError):
                try:
                    return int(float(valor))
                except Exception:
                    return 0

        def get_placeholder_image(categoria):
            placeholders = {
                'Celulares': 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80',
                'Computadores': 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80',
                'Tablets': 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80',
                'Periféricos': 'https://images.unsplash.com/photo-1593640408182-31c70c8268f5?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80',
                'Acessórios': 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80',
                'Games': 'https://images.unsplash.com/photo-1606813907291-d86efa9b94db?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80',
            }
            return placeholders.get(
                categoria,
                'https://images.unsplash.com/photo-1556656793-08538906a9f8?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80',
            )

        json_produtos = []
        for row in retorno_bd:
            imagem = f"/static/tech_trade_imagens/{row[8]}" if row[8] else get_placeholder_image(row[3])
            chave = (row[12] or "").strip() if has_chave_nfe and len(row) > 12 else ""
            json_produtos.append({
                "id_produto": row[0],
                "nome": row[1] or "",
                "descricao": row[2] or "",
                "categoria": row[3] or "",
                "preco": round(safe_float(row[4]), 2),
                "preco_formatado": f"{safe_float(row[4]):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                "estoque": safe_int(row[5]),
                "disponivel": safe_int(row[5]) > 0,
                "criado_em": formata_data(row[6]),
                "criado_por": row[7] or "",
                "imagem": imagem,
                "verificado": bool(row[9]) if len(row) > 9 else True,
                "verificado": row[10] or "",
                "verificado_em": formata_data(row[11]) if len(row) > 11 and row[11] else "",
                "chave_nfe": chave,
                "consulta_nfe_url": URL_CONSULTA_NFE,
            })

        return jsonify({"json_produtos": json_produtos})
    except Exception as err:
        return jsonify({"erro": str(err).replace("'", '"')}), 500


@rotas_produto.route("/techtrade/produtos/checkout/<int:id_produto>", methods=["GET", "POST"])
def checkout(id_produto):
    try:
        conexao = ConexaoBD()
        sql_produto = """
            SELECT
                p.id_produto,
                p.nome,
                p.descricao,
                p.preco,
                p.estoque,
                p.imagem,
                p.verificado,
                p.criado_por,
                p.criado_por_id
            FROM produtos_tt p
            WHERE p.id_produto = %s
        """
        resultado = conexao.select(sql_produto, (id_produto,))
        if not resultado:
            conexao.close()
            abort(404, "Produto não encontrado")

        p = resultado[0]
        produto = {
            "id_produto": p[0],
            "nome": p[1],
            "descricao": p[2],
            "preco": float(p[3]),
            "estoque": int(p[4]),
            "imagem": f"/static/tech_trade_imagens/{p[5]}" if p[5] else "/static/tech_trade_imagens/default.jpg",
            "verificado": bool(p[6]),
            "vendedor": p[7] or "Vendedor não informado",
            "vendedor_id": p[8],
        }

        if request.method == "POST":
            metodo = request.form.get("metodo")
            endereco = request.form.get("endereco", "")
            observacoes = request.form.get("observacoes", "")
            if not metodo:
                conexao.close()
                return "Método de pagamento não selecionado.", 400

            dados_compra = {
                "id_produto": id_produto,
                "metodo_pagamento": metodo,
                "endereco_entrega": endereco,
                "observacoes": observacoes,
            }

            conexao.close()
            with rotas_produto.test_client() as client:
                response = client.post(
                    '/techtrade/produtos/finalizar_compra_completa',
                    json=dados_compra,
                    headers={'Content-Type': 'application/json'},
                )
                if response.status_code == 201:
                    mensagem = f"Compra do produto '{produto['nome']}' realizada com sucesso via {metodo}!"
                    return render_template("confirmacao.html", mensagem=mensagem, produto=produto, metodo=metodo, now=datetime.now())
                erro = response.get_json().get('erro', 'Erro ao processar compra')
                return f"Erro: {erro}", 400

        conexao.close()
        bloqueado = not produto["verificado"]
        return render_template(
            "checkout.html",
            produto=produto,
            bloqueado_verificacao=bloqueado,
            consulta_nfe_url=URL_CONSULTA_NFE,
        )
    except Exception:
        if 'conexao' in locals():
            conexao.close()
        abort(500)


@rotas_produto.route("/comprovante/<int:id_produto>")
def comprovante_compra(id_produto):
    try:
        conexao = ConexaoBD()
        sql_produto = """
            SELECT nome, descricao, preco, criado_por, imagem
            FROM produtos_tt
            WHERE id_produto = %s
        """
        produto_db = conexao.select(sql_produto, (id_produto,))
        conexao.close()
        if not produto_db:
            abort(404)

        produto = {
            "nome": produto_db[0][0],
            "descricao": produto_db[0][1],
            "preco": float(produto_db[0][2]),
            "vendedor": produto_db[0][3] or "TechTrade",
            "imagem": produto_db[0][4] or "default.jpg",
        }
        metodo = request.args.get('metodo', 'PIX')
        return render_template(
            "comprovante.html",
            produto=produto,
            metodo=metodo,
            now=datetime.now(),
            usuario_nome=session.get('usuario_nome', 'Cliente TechTrade'),
        )
    except Exception:
        abort(500)


@rotas_produto.route("/techtrade/produtos/finalizar_compra_completa", methods=["POST"])
def finalizar_compra_completa():
    try:
        if not session.get('usuario_logado'):
            return jsonify({"erro": "Usuário não logado"}), 401

        dados = request.get_json() or {}
        id_produto = dados.get('id_produto')
        metodo_pagamento = dados.get('metodo_pagamento')
        endereco_entrega = dados.get('endereco_entrega', '')
        observacoes = dados.get('observacoes', '')

        if not all([id_produto, metodo_pagamento]):
            return jsonify({"erro": "Dados incompletos"}), 400

        id_cliente = session.get('usuario_id')
        quantidade = 1
        conexao = ConexaoBD()
        sql_produto = """
            SELECT p.preco, p.estoque, p.criado_por_id, p.nome,
                   COALESCE(v.nome, 'Vendedor TechTrade') as vendedor_nome,
                   COALESCE(p.verificado, 0), p.imagem
            FROM produtos_tt p
            LEFT JOIN vendedores_tt v ON p.criado_por_id = v.id_vendedor
            WHERE p.id_produto = %s
        """
        produto_info = conexao.select(sql_produto, (id_produto,))
        if not produto_info:
            conexao.close()
            return jsonify({"erro": "Produto não encontrado"}), 404

        preco_unitario = float(produto_info[0][0])
        estoque_atual = produto_info[0][1]
        id_vendedor = produto_info[0][2]
        nome_produto = produto_info[0][3]
        nome_vendedor = produto_info[0][4]
        produto_verificado = bool(produto_info[0][5])
        imagem_arquivo = produto_info[0][6]
        total = preco_unitario * quantidade

        if not produto_verificado:
            conexao.close()
            return jsonify({
                "erro": "Produto não verificado. Aguarde a administradora confirmar a documentação fiscal antes da compra.",
            }), 400

        if estoque_atual < quantidade:
            conexao.close()
            return jsonify({"erro": "Estoque insuficiente"}), 400

        codigo_rastreio = _gerar_codigo_rastreio()
        has_codigo_col = table_has_column(conexao, "compras_tt", "codigo_rastreio")
        enum_vals = compras_status_enum_values(conexao)
        pode_aguardando = bool(enum_vals and "aguardando_aprovacao" in enum_vals)

        if has_codigo_col:
            for _ in range(12):
                dup = conexao.select(
                    "SELECT 1 FROM compras_tt WHERE codigo_rastreio = %s LIMIT 1",
                    (codigo_rastreio,),
                )
                if not dup:
                    break
                codigo_rastreio = _gerar_codigo_rastreio()

        if pode_aguardando and has_codigo_col:
            status_db = "aguardando_aprovacao"
            obs_db = observacoes or ""
        elif pode_aguardando:
            status_db = "aguardando_aprovacao"
            obs_db = observacoes or ""
        elif has_codigo_col:
            status_db = "pendente"
            obs_db = observacoes or ""
        else:
            status_db = "pendente"
            obs_db = embutir_codigo_em_observacoes(codigo_rastreio, observacoes)

        if has_codigo_col:
            sql_compra = """
                INSERT INTO compras_tt
                (id_cliente, id_produto, quantidade, preco_unitario, total,
                 metodo_pagamento, endereco_entrega, observacoes, status, data_compra, codigo_rastreio)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
            """
            id_compra = conexao.insert(sql_compra, (
                id_cliente, id_produto, quantidade, preco_unitario, total,
                metodo_pagamento, endereco_entrega, obs_db, status_db, codigo_rastreio,
            ))
        else:
            sql_compra = """
                INSERT INTO compras_tt
                (id_cliente, id_produto, quantidade, preco_unitario, total,
                 metodo_pagamento, endereco_entrega, observacoes, status, data_compra)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            id_compra = conexao.insert(sql_compra, (
                id_cliente, id_produto, quantidade, preco_unitario, total,
                metodo_pagamento, endereco_entrega, obs_db, status_db,
            ))

        msg_pedido = (
            f"Novo pedido #{id_compra} aguardando sua aprovação: {nome_produto} — R$ {total:.2f} "
            f"({metodo_pagamento}). Rastreio cliente: {codigo_rastreio}"
        )
        destinatarios = [1]
        if id_vendedor:
            destinatarios.append(id_vendedor)
        _notificar_vendedores(conexao, destinatarios, msg_pedido)

        conexao.close()

        session.pop("carrinho", None)
        imagem_url = f"/static/tech_trade_imagens/{imagem_arquivo}" if imagem_arquivo else "/static/tech_trade_imagens/default.jpg"
        session["produto"] = {
            "id_produto": int(id_produto),
            "id_compra": int(id_compra) if id_compra else None,
            "nome": nome_produto,
            "descricao": f"Descrição do {nome_produto}",
            "preco": preco_unitario,
            "imagem": imagem_url,
            "vendedor": nome_vendedor,
            "codigo_rastreio": codigo_rastreio,
            "status_pedido": status_db,
            "aguardando_aprovacao_admin": True,
        }
        session["mensagem"] = (
            "Pedido registrado! Guarde o código de rastreio. A administradora vai aprovar e liberar a separação."
        )
        session["metodo"] = metodo_pagamento
        session["usuario_nome"] = session.get("usuario_nome", "Cliente")

        return jsonify({
            "mensagem": "Pedido registrado! Aguarde aprovação da administradora.",
            "id_produto": id_produto,
            "id_compra": id_compra,
            "nome_produto": nome_produto,
            "preco": preco_unitario,
            "metodo_pagamento": metodo_pagamento,
            "vendedor": nome_vendedor,
            "codigo_rastreio": codigo_rastreio,
            "notificado": True,
        }), 201
    except Exception as err:
        return jsonify({"erro": str(err)}), 500


def _timeline_status_pedido(status_atual):
    """Etapas exibidas ao cliente no rastreio (marketplace com aprovação administrativa)."""
    status_atual = (status_atual or "").strip().lower()
    if status_atual == "cancelado":
        return [{"label": "Pedido cancelado", "state": "cancelado"}]

    flow = [
        "Pedido recebido — aguardando aprovação da administradora",
        "Aprovado — em preparação para envio",
        "Despachado / em transporte",
        "Entregue",
    ]
    # Índice atual na linha do tempo (pendente legado = mesmo que aguardando)
    rank = {
        "aguardando_aprovacao": 0,
        "pendente": 0,
        "pago": 1,
        "processando": 1,
        "enviado": 2,
        "entregue": 3,
    }
    cur_i = rank.get(status_atual, 0)
    out = []
    for i, label in enumerate(flow):
        if cur_i > i:
            st = "done"
        elif cur_i == i:
            st = "current"
        else:
            st = "todo"
        out.append({"label": label, "state": st})
    return out


@rotas_produto.route("/rastreio", methods=["GET", "POST"])
def rastreio_pedido():
    codigo = (request.args.get("codigo") or request.form.get("codigo") or "").strip()
    erro = None
    pedido_view = None

    if request.method == "POST" or codigo:
        if not codigo:
            erro = "Informe o código de rastreio."
        elif not re.match(r"^TT-[A-Za-z0-9]+$", codigo):
            erro = "Formato de código inválido."
        else:
            try:
                conexao = ConexaoBD()
                has_codigo_col = table_has_column(conexao, "compras_tt", "codigo_rastreio")
                if has_codigo_col:
                    sql = """
                        SELECT c.id_compra, c.status, c.data_compra, c.quantidade, c.total,
                               p.nome, p.imagem
                        FROM compras_tt c
                        JOIN produtos_tt p ON p.id_produto = c.id_produto
                        WHERE c.codigo_rastreio = %s
                        LIMIT 1
                    """
                    row = conexao.select(sql, (codigo,))
                else:
                    like_arg = f"%|COD:{codigo}|%"
                    sql = """
                        SELECT c.id_compra, c.status, c.data_compra, c.quantidade, c.total,
                               p.nome, p.imagem
                        FROM compras_tt c
                        JOIN produtos_tt p ON p.id_produto = c.id_produto
                        WHERE c.observacoes LIKE %s
                        LIMIT 1
                    """
                    row = conexao.select(sql, (like_arg,))
                conexao.close()
                if not row:
                    erro = "Código não encontrado. Verifique e tente novamente."
                else:
                    r = row[0]
                    img = r[6]
                    pedido_view = {
                        "id_compra": r[0],
                        "status": r[1] or "",
                        "data_compra": r[2],
                        "quantidade": int(r[3] or 0),
                        "total": float(r[4] or 0),
                        "produto_nome": r[5] or "",
                        "imagem": f"/static/tech_trade_imagens/{img}" if img else "/static/tech_trade_imagens/default.jpg",
                        "timeline": _timeline_status_pedido(r[1] or ""),
                    }
            except Exception:
                erro = "Não foi possível consultar o rastreio no momento."

    return render_template("rastreio.html", codigo=codigo, erro=erro, pedido=pedido_view, consulta_nfe_url=URL_CONSULTA_NFE)


@rotas_produto.route("/confirmacao")
def confirmacao_compra():
    try:
        produto = session.get('produto')
        metodo = session.get('metodo', 'PIX')
        mensagem = session.get('mensagem', 'Compra realizada com sucesso!')
        if not produto:
            return redirect(url_for('produto.renderizar_produtos'))

        codigo_rastreio = (produto or {}).get("codigo_rastreio") if isinstance(produto, dict) else None
        status_pedido = (produto or {}).get("status_pedido") if isinstance(produto, dict) else None
        id_compra_sessao = (produto or {}).get("id_compra") if isinstance(produto, dict) else None
        aguarda_admin = (produto or {}).get("aguardando_aprovacao_admin") if isinstance(produto, dict) else False

        return render_template(
            "confirmacao.html",
            produto=produto,
            metodo=metodo,
            mensagem=mensagem,
            now=datetime.now(),
            usuario_nome=session.get('usuario_nome', 'Cliente TechTrade'),
            codigo_rastreio=codigo_rastreio,
            status_pedido=status_pedido,
            id_compra_sessao=id_compra_sessao,
            aguardando_aprovacao_admin=aguarda_admin,
        )
    except Exception:
        return "Erro na confirmação", 500


@rotas_produto.route('/suporte_comprador')
def suporte_comprador():
    return render_template('suporte_comprador.html')


def _tabela_notificacoes_cliente_tt(conexao):
    try:
        r = conexao.select(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = DATABASE() AND table_name = %s
            LIMIT 1
            """,
            ("notificacoes_cliente_tt",),
        )
        return bool(r)
    except Exception:
        return False


def _formatar_data_pedido(val):
    if isinstance(val, datetime):
        return val.strftime("%d/%m/%Y %H:%M")
    return str(val) if val else ""


@rotas_produto.route("/meus-pedidos")
def meus_pedidos():
    if not session.get("usuario_logado") or not session.get("usuario_id"):
        return redirect(url_for("produto.login"))
    usuario_foto_url = None
    usuario_iniciais = ""
    try:
        from .produto import _foto_url_cliente, _iniciais_nome
    except ImportError:
        from produto import _foto_url_cliente, _iniciais_nome
    try:
        uid = int(session["usuario_id"])
        usuario_foto_url = _foto_url_cliente(uid) or None
    except Exception:
        usuario_foto_url = None
    try:
        usuario_iniciais = _iniciais_nome(session.get("usuario_nome"))
    except Exception:
        usuario_iniciais = ""
    _marcar_url = url_for("produto.cliente_notificacao_marcar_lida", id_notificacao=0)
    marcar_lida_prefix = _marcar_url.rpartition("/")[0] + "/"
    return render_template(
        "meus_pedidos.html",
        consulta_nfe_url=URL_CONSULTA_NFE,
        usuario_foto_url=usuario_foto_url,
        usuario_iniciais=usuario_iniciais,
        static_css_checkout=url_for("static", filename="css/checkout.css"),
        static_css_meus_pedidos=url_for("static", filename="css/meus_pedidos.css"),
        static_js_meus_pedidos=url_for("static", filename="js/meus_pedidos.js"),
        api_pedidos_url=url_for("produto.cliente_pedidos_json"),
        api_notifs_url=url_for("produto.cliente_notificacoes_json"),
        marcar_lida_prefix=marcar_lida_prefix,
    )


@rotas_produto.route("/techtrade/cliente/pedidos/json", methods=["GET"])
def cliente_pedidos_json():
    if not session.get("usuario_logado") or not session.get("usuario_id"):
        return jsonify({"erro": "Faça login para ver seus pedidos."}), 401
    try:
        id_cliente = int(session["usuario_id"])
        conexao = ConexaoBD()
        has_cr = table_has_column(conexao, "compras_tt", "codigo_rastreio")
        campos = """
            SELECT c.id_compra, c.status, c.data_compra, c.quantidade, c.total,
                   c.metodo_pagamento, c.endereco_entrega,
                   p.nome, p.imagem, p.id_produto
        """
        if has_cr:
            sql = campos + ", c.codigo_rastreio FROM compras_tt c JOIN produtos_tt p ON p.id_produto = c.id_produto WHERE c.id_cliente = %s ORDER BY c.data_compra DESC"
        else:
            sql = campos + ", c.observacoes FROM compras_tt c JOIN produtos_tt p ON p.id_produto = c.id_produto WHERE c.id_cliente = %s ORDER BY c.data_compra DESC"
        rows = conexao.select(sql, (id_cliente,))
        conexao.close()

        out = []
        for r in rows or []:
            if has_cr:
                id_c, status, data_c, qtd, total, metodo, endereco, nome_p, img, id_prod, codigo = (
                    r[0],
                    r[1],
                    r[2],
                    r[3],
                    r[4],
                    r[5],
                    r[6],
                    r[7],
                    r[8],
                    r[9],
                    (r[10] or "").strip(),
                )
            else:
                id_c, status, data_c, qtd, total, metodo, endereco, nome_p, img, id_prod, obs = (
                    r[0],
                    r[1],
                    r[2],
                    r[3],
                    r[4],
                    r[5],
                    r[6],
                    r[7],
                    r[8],
                    r[9],
                    r[10],
                )
                codigo = extrair_codigo_rastreio_obs(obs or "")
            img_url = f"/static/tech_trade_imagens/{img}" if img else "/static/tech_trade_imagens/default.jpg"
            st = (status or "").strip().lower()
            out.append(
                {
                    "id_compra": id_c,
                    "status": status or "",
                    "status_label": (status or "").replace("_", " ").title(),
                    "data_compra": _formatar_data_pedido(data_c),
                    "quantidade": int(qtd or 0),
                    "total": float(total or 0),
                    "total_formatado": f"{float(total or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    "metodo_pagamento": metodo or "",
                    "endereco_entrega": endereco or "",
                    "produto_nome": nome_p or "",
                    "id_produto": id_prod,
                    "imagem": img_url,
                    "codigo_rastreio": codigo,
                    "timeline": _timeline_status_pedido(st),
                    "rastreio_url": url_for("produto.rastreio_pedido", codigo=codigo) if codigo else url_for("produto.rastreio_pedido"),
                }
            )
        return jsonify({"pedidos": out})
    except Exception as err:
        return jsonify({"erro": str(err)}), 500


@rotas_produto.route("/techtrade/cliente/notificacoes/json", methods=["GET"])
def cliente_notificacoes_json():
    if not session.get("usuario_logado") or not session.get("usuario_id"):
        return jsonify({"erro": "Não autorizado"}), 401
    try:
        id_cliente = int(session["usuario_id"])
        conexao = ConexaoBD()
        if not _tabela_notificacoes_cliente_tt(conexao):
            conexao.close()
            return jsonify({"notificacoes": [], "aviso_tabela": True})
        rows = conexao.select(
            """
            SELECT id_notificacao, mensagem, data_envio, lida, id_compra
            FROM notificacoes_cliente_tt
            WHERE id_cliente = %s
            ORDER BY data_envio DESC
            LIMIT 50
            """,
            (id_cliente,),
        )
        conexao.close()
        lista = []
        for row in rows or []:
            lista.append(
                {
                    "id_notificacao": row[0],
                    "mensagem": row[1] or "",
                    "data_envio": row[2].strftime("%d/%m/%Y %H:%M") if isinstance(row[2], datetime) else str(row[2]),
                    "lida": bool(row[3]),
                    "id_compra": row[4],
                }
            )
        return jsonify({"notificacoes": lista, "aviso_tabela": False})
    except Exception as err:
        return jsonify({"erro": str(err)}), 500


@rotas_produto.route("/techtrade/cliente/notificacoes/marcar_lida/<int:id_notificacao>", methods=["POST"])
def cliente_notificacao_marcar_lida(id_notificacao):
    if not session.get("usuario_logado") or not session.get("usuario_id"):
        return jsonify({"erro": "Não autorizado"}), 401
    try:
        id_cliente = int(session["usuario_id"])
        conexao = ConexaoBD()
        if not _tabela_notificacoes_cliente_tt(conexao):
            conexao.close()
            return jsonify({"mensagem": "ok"}), 200
        conexao.update(
            "UPDATE notificacoes_cliente_tt SET lida = 1 WHERE id_notificacao = %s AND id_cliente = %s",
            (id_notificacao, id_cliente),
        )
        conexao.close()
        return jsonify({"mensagem": "ok"}), 200
    except Exception as err:
        return jsonify({"erro": str(err)}), 500