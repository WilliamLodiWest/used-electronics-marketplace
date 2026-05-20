from datetime import datetime
import os
from flask import flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash
from src.utils.bd import ConexaoBD
from src.utils.schema_compat import (
    compras_status_enum_values,
    extrair_codigo_rastreio_obs,
    pedido_aguarda_aprovacao_admin,
    table_has_column,
)

try:
    from .produto import rotas_produto
except ImportError:
    from produto import rotas_produto

# ------------------- SISTEMA VENDEDOR -------------------
ADMIN_EMAIL = "giovanna.markxs@gmail.com"
ADMIN_SENHA = "1234"
BASE_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PERFIS_CLIENTES_DIR = os.path.join(BASE_APP_DIR, 'static', 'perfis_clientes')
_IMAGENS_PRODUTOS_DIR = os.path.join(BASE_APP_DIR, 'static', 'tech_trade_imagens')
_FOTO_EXTS = ('.webp', '.png', '.jpg', '.jpeg')


def _admin_autenticada():
    return bool(
        session.get('vendedor_logado')
        and session.get('is_admin')
        and session.get('vendedor_email') == ADMIN_EMAIL
    )


def _garantir_vendedor_admin(conexao):
    """Garante id_vendedor válido em vendedores_tt (evita erro de FK ao inserir produto)."""
    rows = conexao.select(
        "SELECT id_vendedor FROM vendedores_tt WHERE email = %s LIMIT 1",
        (ADMIN_EMAIL,),
    )
    if rows:
        id_vendedor = int(rows[0][0])
    else:
        hash_senha = generate_password_hash(ADMIN_SENHA, method='pbkdf2:sha256')
        id_vendedor = conexao.insert(
            """
            INSERT INTO vendedores_tt (nome, email, senha, telefone, documento, descricao, aprovado, data_cadastro)
            VALUES (%s, %s, %s, %s, %s, %s, 1, NOW())
            """,
            (
                "Administradora",
                ADMIN_EMAIL,
                hash_senha,
                "",
                "ADMIN",
                "Conta administrativa TechTrade",
            ),
        )
        if not id_vendedor:
            rows = conexao.select(
                "SELECT id_vendedor FROM vendedores_tt WHERE email = %s LIMIT 1",
                (ADMIN_EMAIL,),
            )
            id_vendedor = int(rows[0][0]) if rows else 1

    session['vendedor_id'] = id_vendedor
    session['vendedor_nome'] = session.get('vendedor_nome') or "Administradora"
    return id_vendedor


def _categoria_existe(conexao, categoria_id):
    rows = conexao.select(
        "SELECT 1 FROM categorias_produtos_tt WHERE id_categoria = %s LIMIT 1",
        (int(categoria_id),),
    )
    return bool(rows)


def _inserir_produto_admin(conexao, nome, descricao, categoria_id, preco, estoque, imagem=None):
    id_vendedor = _garantir_vendedor_admin(conexao)
    if not _categoria_existe(conexao, categoria_id):
        raise ValueError("Categoria inválida. Selecione uma categoria cadastrada.")

    sql = """
        INSERT INTO produtos_tt (nome, descricao, categoria_id, preco, estoque,
                               criado_por, criado_por_id, imagem, verificado, criado_em)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, NOW())
    """
    return conexao.insert(
        sql,
        (
            nome,
            descricao,
            int(categoria_id),
            float(preco),
            int(estoque),
            session.get('vendedor_nome'),
            id_vendedor,
            imagem,
        ),
    )


def _foto_url_admin(id_admin):
    if not id_admin:
        return None
    for ext in _FOTO_EXTS:
        caminho = os.path.join(_PERFIS_CLIENTES_DIR, f'{id_admin}{ext}')
        if os.path.isfile(caminho):
            return f'/static/perfis_clientes/{id_admin}{ext}'
    return None


def _iniciais_nome(nome):
    nome = (nome or '').strip()
    if not nome:
        return ''
    partes = [p for p in nome.split() if p]
    if len(partes) >= 2:
        return (partes[0][0] + partes[-1][0]).upper()
    return nome[:2].upper()


def _normalizar_imagem_produto(imagem_valor):
    """Mantém apenas o nome do arquivo para imagens locais."""
    if not imagem_valor:
        return None

    imagem = str(imagem_valor).strip()
    if not imagem:
        return None

    if imagem.startswith('http://') or imagem.startswith('https://'):
        return imagem

    imagem = imagem.replace('\\', '/')
    while '//' in imagem:
        imagem = imagem.replace('//', '/')

    if 'tech_trade_imagens/' in imagem:
        imagem = imagem.split('tech_trade_imagens/')[-1]

    if imagem.startswith('/'):
        imagem = imagem[1:]

    return imagem or None


def _montar_url_imagem_produto(imagem_valor):
    imagem_normalizada = _normalizar_imagem_produto(imagem_valor)
    if not imagem_normalizada:
        return "/static/img/sem-imagem.png"
    if imagem_normalizada.startswith('http://') or imagem_normalizada.startswith('https://'):
        return imagem_normalizada
    return f"/static/tech_trade_imagens/{imagem_normalizada}"


def _tabela_notificacoes_cliente_existe(conexao):
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


def _notificar_cliente_pedido_confirmado(conexao, id_cliente, id_compra, nome_produto, codigo_rastreio):
    """Avisa o comprador que o pedido foi confirmado (tabela opcional — ver sql/notificacoes_cliente_tt.sql)."""
    if not id_cliente or not _tabela_notificacoes_cliente_existe(conexao):
        return
    nome_produto = (nome_produto or "seu produto").strip()
    msg = (
        f"Pedido #{id_compra} confirmado pela administradora. "
        f"O produto \"{nome_produto}\" teve baixa no estoque e está em preparação para envio."
    )
    if codigo_rastreio:
        msg += f" Rastreio: {codigo_rastreio}."
    try:
        conexao.insert(
            """
            INSERT INTO notificacoes_cliente_tt (id_cliente, id_compra, mensagem, data_envio, lida)
            VALUES (%s, %s, %s, NOW(), 0)
            """,
            (id_cliente, id_compra, msg),
        )
    except Exception:
        pass


@rotas_produto.route('/vendedor/login', methods=['GET', 'POST'])
def vendedor_login():
    """Login específico para vendedores"""
    try:
        if request.method == 'POST':
            email = request.form.get('email')
            senha = request.form.get('senha')
            
            if not email or not senha:
                return render_template('vendedor_login.html', erro="Preencha todos os campos.")

            # Acesso único da administradora.
            if email.lower().strip() == ADMIN_EMAIL and senha == ADMIN_SENHA:
                session['vendedor_logado'] = True
                session['vendedor_nome'] = "Administradora"
                session['vendedor_email'] = ADMIN_EMAIL
                session['is_admin'] = True
                conexao = ConexaoBD()
                _garantir_vendedor_admin(conexao)
                conexao.close()
                return redirect(url_for('produto.vendedor_dashboard'))

            return render_template(
                'vendedor_login.html',
                erro="Acesso permitido apenas para a administradora."
            )
        
        return render_template('vendedor_login.html')
    
    except Exception as err:
        return render_template('vendedor_login.html', erro=f"Erro ao realizar login: {str(err)}")


@rotas_produto.route('/vendedor/cadastro', methods=['GET', 'POST'])
def vendedor_cadastro():
    """Cadastro de novos vendedores"""
    try:
        if request.method == 'POST':
            nome = request.form.get('nome')
            email = request.form.get('email')
            telefone = request.form.get('telefone')
            documento = request.form.get('documento')
            descricao = request.form.get('descricao')
            senha = request.form.get('senha')
            confirmar_senha = request.form.get('confirmar_senha')
            
            # Validação dos campos
            if not all([nome, email, telefone, documento, descricao, senha]):
                return render_template('vendedor_cadastro.html', erro="Preencha todos os campos obrigatórios.")

            if email.lower().strip() != ADMIN_EMAIL:
                return render_template(
                    'vendedor_cadastro.html',
                    erro="Apenas a administradora autorizada pode ter conta de vendedor."
                )
            
            if senha != confirmar_senha:
                return render_template('vendedor_cadastro.html', erro="As senhas não conferem.")
            
            if email.lower().strip() != ADMIN_EMAIL and len(senha) < 6:
                return render_template('vendedor_cadastro.html', erro="A senha deve ter no mínimo 6 caracteres.")
            
            conexao = ConexaoBD()
            
            # Verificar se email já existe
            verifica_email = conexao.select("SELECT id_vendedor FROM vendedores_tt WHERE email = %s", (email,))
            if verifica_email:
                conexao.close()
                return render_template('vendedor_cadastro.html', erro="E-mail já cadastrado.")
            
            # Verificar se documento já existe
            verifica_doc = conexao.select("SELECT id_vendedor FROM vendedores_tt WHERE documento = %s", (documento,))
            if verifica_doc:
                conexao.close()
                return render_template('vendedor_cadastro.html', erro="Documento já cadastrado.")
            
            hash_senha = generate_password_hash(senha, method='pbkdf2:sha256')
            
            sql_insert = """
                INSERT INTO vendedores_tt (nome, email, senha, telefone, documento, descricao, aprovado, data_cadastro)
                VALUES (%s, %s, %s, %s, %s, %s, 0, NOW())
            """
            conexao.insert(sql_insert, (nome, email, hash_senha, telefone, documento, descricao))
            conexao.close()
            
            flash("Cadastro realizado com sucesso! Aguarde a aprovação do administrador.", "sucesso")
            return redirect(url_for('produto.vendedor_login'))
        
        return render_template('vendedor_cadastro.html')
    
    except Exception as err:
        return render_template('vendedor_cadastro.html', erro=f"Erro ao cadastrar: {str(err)}")


@rotas_produto.route('/vendedor/dashboard')
def vendedor_dashboard():
    """Dashboard principal do vendedor"""
    if not _admin_autenticada():
        return redirect(url_for('produto.vendedor_login'))
    
    try:
        conexao = ConexaoBD()
        id_vendedor = _garantir_vendedor_admin(conexao)
        
        # Estatísticas do vendedor
        stats = {}
        
        # Total de produtos
        sql_produtos = "SELECT COUNT(*) FROM produtos_tt WHERE criado_por_id = %s"
        result = conexao.select(sql_produtos, (id_vendedor,))
        stats['total_produtos'] = result[0][0] if result else 0
        
        # Produtos com baixo estoque (< 10)
        sql_baixo_estoque = "SELECT COUNT(*) FROM produtos_tt WHERE criado_por_id = %s AND estoque < 10"
        result = conexao.select(sql_baixo_estoque, (id_vendedor,))
        stats['baixo_estoque'] = result[0][0] if result else 0
        
        # Total de vendas concluídas
        sql_vendas = """
            SELECT COUNT(*), COALESCE(SUM(c.total), 0)
            FROM compras_tt c
            JOIN produtos_tt p ON c.id_produto = p.id_produto
            WHERE p.criado_por_id = %s AND c.status = 'entregue'
        """
        result = conexao.select(sql_vendas, (id_vendedor,))
        stats['total_vendas'] = result[0][0] if result else 0
        stats['faturamento'] = float(result[0][1]) if result and result[0][1] else 0
        
        # Total de pedidos pendentes
        sql_pedidos_pendentes = """
            SELECT COUNT(*)
            FROM compras_tt c
            JOIN produtos_tt p ON c.id_produto = p.id_produto
            WHERE p.criado_por_id = %s AND c.status IN ('pendente', 'pago', 'processando')
        """
        result = conexao.select(sql_pedidos_pendentes, (id_vendedor,))
        stats['pedidos_pendentes'] = result[0][0] if result else 0
        
        # Total de notificações não lidas
        sql_notificacoes = "SELECT COUNT(*) FROM notificacoes_tt WHERE id_vendedor = %s AND lida = 0"
        result = conexao.select(sql_notificacoes, (id_vendedor,))
        stats['notificacoes'] = result[0][0] if result else 0
        
        # Últimas vendas
        sql_ultimas_vendas = """
            SELECT c.id_compra, p.nome, c.quantidade, c.total, c.data_compra, c.status, c.metodo_pagamento,
                   cl.nome as cliente_nome
            FROM compras_tt c
            JOIN produtos_tt p ON c.id_produto = p.id_produto
            JOIN clientes_tt cl ON c.id_cliente = cl.id_cliente
            WHERE p.criado_por_id = %s
            ORDER BY c.data_compra DESC
            LIMIT 10
        """
        ultimas_vendas = conexao.select(sql_ultimas_vendas, (id_vendedor,))
        
        # Notificações recentes
        sql_notificacoes_recentes = """
            SELECT id_notificacao, mensagem, data_envio, lida
            FROM notificacoes_tt
            WHERE id_vendedor = %s
            ORDER BY data_envio DESC
            LIMIT 10
        """
        notificacoes = conexao.select(sql_notificacoes_recentes, (id_vendedor,))
        
        # Lista de produtos para o dashboard
        sql_produtos_lista = """
            SELECT p.id_produto, p.nome, p.preco, p.estoque, p.imagem, p.verificado,
                   c.nome as categoria
            FROM produtos_tt p
            LEFT JOIN categorias_produtos_tt c ON p.categoria_id = c.id_categoria
            WHERE p.criado_por_id = %s
            ORDER BY p.criado_em DESC
            LIMIT 6
        """
        produtos = conexao.select(sql_produtos_lista, (id_vendedor,))
        
        # Categorias para os formulários
        categorias = conexao.select("SELECT id_categoria, nome FROM categorias_produtos_tt ORDER BY nome")
        
        conexao.close()
        
        vendedor_nome = session.get('vendedor_nome')
        vendedor_foto_url = _foto_url_admin(id_vendedor)
        vendedor_iniciais = _iniciais_nome(vendedor_nome)

        return render_template('vendedor_painel.html', 
                             stats=stats,
                             produtos=produtos,
                             ultimas_vendas=ultimas_vendas, 
                             notificacoes=notificacoes,
                             categorias=categorias,
                             vendedor_nome=vendedor_nome,
                             vendedor_foto_url=vendedor_foto_url,
                             vendedor_iniciais=vendedor_iniciais)
    
    except Exception as err:
        vendedor_nome = session.get('vendedor_nome')
        return render_template(
            'vendedor_painel.html',
            erro=str(err),
            vendedor_nome=vendedor_nome,
            vendedor_foto_url=None,
            vendedor_iniciais=_iniciais_nome(vendedor_nome),
        )


@rotas_produto.route('/vendedor/produtos/adicionar', methods=['POST'])
def vendedor_adicionar_produto():
    """Adicionar novo produto"""
    if not _admin_autenticada():
        return jsonify({"erro": "Não autorizado"}), 401
    
    try:
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        categoria_id = request.form.get('categoria_id')
        preco = request.form.get('preco')
        estoque = request.form.get('estoque')
        imagem = request.files.get('imagem')
        
        if not all([nome, descricao, categoria_id, preco, estoque]):
            return jsonify({"erro": "Preencha todos os campos obrigatórios"}), 400
        
        # Converter valores
        preco = float(preco.replace(',', '.')) if isinstance(preco, str) else float(preco)
        estoque = int(estoque)
        id_vendedor = session.get('vendedor_id')
        vendedor_nome = session.get('vendedor_nome')
        
        # Processar imagem
        nome_imagem = None
        if imagem and imagem.filename:
            from werkzeug.utils import secure_filename
            extensao = imagem.filename.rsplit('.', 1)[-1].lower()
            nome_imagem = secure_filename(f"prod_{id_vendedor}_{int(datetime.now().timestamp())}.{extensao}")
            os.makedirs(_IMAGENS_PRODUTOS_DIR, exist_ok=True)
            caminho = os.path.join(_IMAGENS_PRODUTOS_DIR, nome_imagem)
            imagem.save(caminho)
        
        conexao = ConexaoBD()
        _inserir_produto_admin(conexao, nome, descricao, categoria_id, preco, estoque, nome_imagem)
        conexao.close()
        
        return jsonify({"success": True, "mensagem": "Produto adicionado com sucesso!"}), 200
    
    except ValueError as err:
        return jsonify({"success": False, "erro": str(err)}), 400
    except Exception as err:
        return jsonify({"success": False, "erro": str(err)}), 500


@rotas_produto.route('/vendedor/produto/buscar/<int:id_produto>')
def vendedor_buscar_produto(id_produto):
    """Buscar dados de um produto para edição"""
    if not _admin_autenticada():
        return jsonify({"erro": "Não autorizado"}), 401
    
    try:
        conexao = ConexaoBD()
        id_vendedor = session.get('vendedor_id')
        
        sql = """
            SELECT id_produto, nome, descricao, categoria_id, preco, estoque
            FROM produtos_tt
            WHERE id_produto = %s AND criado_por_id = %s
        """
        produto = conexao.select(sql, (id_produto, id_vendedor))
        conexao.close()
        
        if not produto:
            return jsonify({"erro": "Produto não encontrado"}), 404
        
        p = produto[0]
        return jsonify({
            "id_produto": p[0],
            "nome": p[1],
            "descricao": p[2],
            "categoria_id": p[3],
            "preco": float(p[4]),
            "estoque": p[5]
        })
    
    except Exception as err:
        return jsonify({"erro": str(err)}), 500


@rotas_produto.route('/vendedor/produtos/editar/<int:id_produto>', methods=['POST'])
def vendedor_editar_produto(id_produto):
    """Editar produto existente"""
    if not _admin_autenticada():
        return jsonify({"erro": "Não autorizado"}), 401
    
    try:
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        categoria_id = request.form.get('categoria_id')
        preco = request.form.get('preco')
        estoque = request.form.get('estoque')
        
        if not all([nome, descricao, categoria_id, preco, estoque]):
            return jsonify({"erro": "Preencha todos os campos"}), 400
        
        preco = float(preco.replace(',', '.')) if isinstance(preco, str) else float(preco)
        estoque = int(estoque)
        id_vendedor = session.get('vendedor_id')
        
        conexao = ConexaoBD()
        
        # Verificar se o produto pertence ao vendedor
        verifica = conexao.select("SELECT id_produto FROM produtos_tt WHERE id_produto = %s AND criado_por_id = %s", 
                                 (id_produto, id_vendedor))
        if not verifica:
            conexao.close()
            return jsonify({"erro": "Produto não encontrado"}), 404
        
        sql = """
            UPDATE produtos_tt 
            SET nome = %s, descricao = %s, categoria_id = %s, preco = %s, estoque = %s
            WHERE id_produto = %s AND criado_por_id = %s
        """
        conexao.update(sql, (nome, descricao, categoria_id, preco, estoque, id_produto, id_vendedor))
        conexao.close()
        
        return jsonify({"mensagem": "Produto atualizado com sucesso!"}), 200
    
    except Exception as err:
        return jsonify({"erro": str(err)}), 500


@rotas_produto.route('/vendedor/produtos/excluir/<int:id_produto>', methods=['DELETE'])
def vendedor_excluir_produto(id_produto):
    """Excluir produto"""
    if not _admin_autenticada():
        return jsonify({"erro": "Não autorizado"}), 401
    
    try:
        id_vendedor = session.get('vendedor_id')
        
        conexao = ConexaoBD()
        
        # Verificar se o produto pertence ao vendedor
        verifica = conexao.select("SELECT id_produto FROM produtos_tt WHERE id_produto = %s AND criado_por_id = %s", 
                                 (id_produto, id_vendedor))
        if not verifica:
            conexao.close()
            return jsonify({"erro": "Produto não encontrado"}), 404
        
        # Verificar se o produto tem vendas
        tem_vendas = conexao.select("SELECT id_compra FROM compras_tt WHERE id_produto = %s AND status != 'cancelado' LIMIT 1", (id_produto,))
        if tem_vendas:
            conexao.close()
            return jsonify({"erro": "Não é possível excluir um produto que já possui vendas"}), 400
        
        sql = "DELETE FROM produtos_tt WHERE id_produto = %s AND criado_por_id = %s"
        conexao.delete(sql, (id_produto, id_vendedor))
        conexao.close()
        
        return jsonify({"mensagem": "Produto excluído com sucesso!"}), 200
    
    except Exception as err:
        return jsonify({"erro": str(err)}), 500


@rotas_produto.route('/vendedor/pedidos/json')
def vendedor_pedidos_json():
    """Retorna pedidos em JSON para AJAX"""
    if not _admin_autenticada():
        return jsonify({"erro": "Não autorizado"}), 401
    
    try:
        conexao = ConexaoBD()
        id_vendedor = session.get('vendedor_id')
        has_cr = table_has_column(conexao, "compras_tt", "codigo_rastreio")
        sql_obs = """
            SELECT c.id_compra, p.nome as produto_nome, c.quantidade, c.total,
                   c.metodo_pagamento, c.status, c.data_compra, c.endereco_entrega,
                   cl.nome as cliente_nome, cl.email as cliente_email, cl.telefone as cliente_telefone,
                   c.observacoes
        """
        if has_cr:
            sql = sql_obs + ", c.codigo_rastreio FROM compras_tt c JOIN produtos_tt p ON c.id_produto = p.id_produto JOIN clientes_tt cl ON c.id_cliente = cl.id_cliente WHERE p.criado_por_id = %s ORDER BY c.data_compra DESC"
        else:
            sql = sql_obs + " FROM compras_tt c JOIN produtos_tt p ON c.id_produto = p.id_produto JOIN clientes_tt cl ON c.id_cliente = cl.id_cliente WHERE p.criado_por_id = %s ORDER BY c.data_compra DESC"
        pedidos = conexao.select(sql, (id_vendedor,))
        conexao.close()
        
        pedidos_json = []
        for p in pedidos:
            obs = (p[11] or "") if len(p) > 11 else ""
            codigo_col = ((p[12] or "").strip() if has_cr and len(p) > 12 else "")
            codigo_exibir = codigo_col or extrair_codigo_rastreio_obs(obs)
            aguarda = pedido_aguarda_aprovacao_admin(p[5], obs, codigo_col)
            pedidos_json.append({
                "id_compra": p[0],
                "produto_nome": p[1],
                "quantidade": p[2],
                "total": float(p[3]),
                "total_formatado": f"{float(p[3]):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                "metodo_pagamento": p[4],
                "status": p[5],
                "data_compra": p[6].strftime('%d/%m/%Y %H:%M') if p[6] else '-',
                "endereco_entrega": p[7] or 'Não informado',
                "cliente_nome": p[8],
                "cliente_email": p[9],
                "cliente_telefone": p[10] or 'Não informado',
                "codigo_rastreio": codigo_exibir,
                "aguarda_aprovacao_admin": aguarda,
            })
        
        return jsonify(pedidos_json)
    
    except Exception as err:
        return jsonify({"erro": str(err)}), 500


@rotas_produto.route('/vendedor/pedidos/atualizar_status/<int:id_pedido>', methods=['POST'])
def vendedor_atualizar_status_pedido(id_pedido):
    """Atualizar status do pedido"""
    if not _admin_autenticada():
        return jsonify({"erro": "Não autorizado"}), 401
    
    try:
        data = request.get_json()
        status = data.get('status') if data else request.form.get('status')
        
        if not status:
            return jsonify({"erro": "Status não informado"}), 400
        
        id_vendedor = session.get('vendedor_id')
        
        conexao = ConexaoBD()
        
        # Verificar se o pedido pertence ao vendedor
        verifica = """
            SELECT c.id_compra, p.nome, cl.nome as cliente_nome, cl.email as cliente_email
            FROM compras_tt c
            JOIN produtos_tt p ON c.id_produto = p.id_produto
            JOIN clientes_tt cl ON c.id_cliente = cl.id_cliente
            WHERE c.id_compra = %s AND p.criado_por_id = %s
        """
        pedido = conexao.select(verifica, (id_pedido, id_vendedor))
        
        if not pedido:
            conexao.close()
            return jsonify({"erro": "Pedido não encontrado"}), 404
        
        status_validos = [
            'aguardando_aprovacao',
            'pendente',
            'pago',
            'processando',
            'enviado',
            'entregue',
            'cancelado',
        ]
        enum_vals = compras_status_enum_values(conexao)
        if enum_vals:
            status_validos = [s for s in status_validos if s in enum_vals]
        if status not in status_validos:
            conexao.close()
            return jsonify({"erro": "Status inválido"}), 400
        
        sql = "UPDATE compras_tt SET status = %s WHERE id_compra = %s"
        conexao.update(sql, (status, id_pedido))
        conexao.close()
        
        return jsonify({"mensagem": f"Status do pedido atualizado para {status} com sucesso!"}), 200
    
    except Exception as err:
        return jsonify({"erro": str(err)}), 500


@rotas_produto.route('/vendedor/pedidos/aprovar/<int:id_pedido>', methods=['POST'])
def vendedor_aprovar_pedido(id_pedido):
    """Dá baixa no estoque e libera o pedido para preparação (após conferência administrativa)."""
    if not _admin_autenticada():
        return jsonify({"erro": "Não autorizado"}), 401

    try:
        id_vendedor = session.get('vendedor_id')
        conexao = ConexaoBD()
        has_cr = table_has_column(conexao, "compras_tt", "codigo_rastreio")
        sel = "c.status, c.observacoes, c.quantidade, c.id_produto, p.estoque, c.id_cliente, p.nome"
        if has_cr:
            sel += ", c.codigo_rastreio"
        sql_pedido = f"""
            SELECT {sel}
            FROM compras_tt c
            JOIN produtos_tt p ON c.id_produto = p.id_produto
            WHERE c.id_compra = %s AND p.criado_por_id = %s
        """
        row = conexao.select(sql_pedido, (id_pedido, id_vendedor))
        if not row:
            conexao.close()
            return jsonify({"erro": "Pedido não encontrado"}), 404

        r0 = row[0]
        status_atual = r0[0]
        obs = r0[1] or ""
        quantidade = int(r0[2] or 0)
        id_produto = r0[3]
        estoque = int(r0[4] or 0)
        id_cliente = int(r0[5] or 0)
        nome_produto = (r0[6] or "").strip()
        codigo_col = ((r0[7] or "").strip() if has_cr and len(r0) > 7 else "")

        if not pedido_aguarda_aprovacao_admin(status_atual, obs, codigo_col):
            conexao.close()
            return jsonify({"erro": "Este pedido não está aguardando aprovação."}), 400

        if estoque < quantidade:
            conexao.close()
            return jsonify({"erro": "Estoque insuficiente para aprovar este pedido."}), 400

        conexao.update(
            "UPDATE compras_tt SET status = %s WHERE id_compra = %s",
            ('processando', id_pedido),
        )
        conexao.update(
            "UPDATE produtos_tt SET estoque = estoque - %s WHERE id_produto = %s",
            (quantidade, id_produto),
        )
        codigo_exibir = codigo_col or extrair_codigo_rastreio_obs(obs)
        _notificar_cliente_pedido_confirmado(
            conexao, id_cliente, id_pedido, nome_produto, codigo_exibir,
        )
        conexao.close()
        return jsonify({"mensagem": "Pedido aprovado. Estoque atualizado e separação liberada."}), 200
    except Exception as err:
        return jsonify({"erro": str(err)}), 500


@rotas_produto.route('/vendedor/pedidos/reprovar/<int:id_pedido>', methods=['POST'])
def vendedor_reprovar_pedido(id_pedido):
    """Cancela pedido ainda não aprovado (sem alterar estoque)."""
    if not _admin_autenticada():
        return jsonify({"erro": "Não autorizado"}), 401

    try:
        id_vendedor = session.get('vendedor_id')
        conexao = ConexaoBD()
        has_cr = table_has_column(conexao, "compras_tt", "codigo_rastreio")
        sel = "c.status, c.observacoes"
        if has_cr:
            sel += ", c.codigo_rastreio"
        sql_pedido = f"""
            SELECT {sel}
            FROM compras_tt c
            JOIN produtos_tt p ON c.id_produto = p.id_produto
            WHERE c.id_compra = %s AND p.criado_por_id = %s
        """
        row = conexao.select(sql_pedido, (id_pedido, id_vendedor))
        if not row:
            conexao.close()
            return jsonify({"erro": "Pedido não encontrado"}), 404

        r0 = row[0]
        status_atual = r0[0]
        obs = r0[1] or ""
        codigo_col = ((r0[2] or "").strip() if has_cr and len(r0) > 2 else "")
        if not pedido_aguarda_aprovacao_admin(status_atual, obs, codigo_col):
            conexao.close()
            return jsonify({"erro": "Somente pedidos aguardando aprovação podem ser reprovados assim."}), 400

        conexao.update(
            "UPDATE compras_tt SET status = %s WHERE id_compra = %s",
            ('cancelado', id_pedido),
        )
        conexao.close()
        return jsonify({"mensagem": "Pedido cancelado."}), 200
    except Exception as err:
        return jsonify({"erro": str(err)}), 500


@rotas_produto.route('/vendedor/notificacoes/marcar_lida/<int:id_notificacao>', methods=['POST'])
def vendedor_marcar_notificacao_lida(id_notificacao):
    """Marcar notificação como lida"""
    if not _admin_autenticada():
        return jsonify({"erro": "Não autorizado"}), 401
    
    try:
        id_vendedor = session.get('vendedor_id')
        
        conexao = ConexaoBD()
        sql = "UPDATE notificacoes_tt SET lida = 1 WHERE id_notificacao = %s AND id_vendedor = %s"
        conexao.update(sql, (id_notificacao, id_vendedor))
        conexao.close()
        
        return jsonify({"mensagem": "Notificação marcada como lida"}), 200
    
    except Exception as err:
        return jsonify({"erro": str(err)}), 500


@rotas_produto.route('/vendedor/relatorios/json')
def vendedor_relatorios_json():
    """Retorna dados de relatórios em JSON para AJAX"""
    if not _admin_autenticada():
        return jsonify({"erro": "Não autorizado"}), 401
    
    try:
        conexao = ConexaoBD()
        id_vendedor = session.get('vendedor_id')
        
        # Vendas do mês atual
        sql_vendas_mes = """
            SELECT COUNT(*), COALESCE(SUM(c.total), 0)
            FROM compras_tt c
            JOIN produtos_tt p ON c.id_produto = p.id_produto
            WHERE p.criado_por_id = %s 
            AND c.status = 'entregue'
            AND MONTH(c.data_compra) = MONTH(CURRENT_DATE())
            AND YEAR(c.data_compra) = YEAR(CURRENT_DATE())
        """
        vendas_mes = conexao.select(sql_vendas_mes, (id_vendedor,))
        
        # Vendas do mês anterior para comparação
        sql_vendas_mes_anterior = """
            SELECT COUNT(*), COALESCE(SUM(c.total), 0)
            FROM compras_tt c
            JOIN produtos_tt p ON c.id_produto = p.id_produto
            WHERE p.criado_por_id = %s 
            AND c.status = 'entregue'
            AND MONTH(c.data_compra) = MONTH(CURRENT_DATE() - INTERVAL 1 MONTH)
            AND YEAR(c.data_compra) = YEAR(CURRENT_DATE() - INTERVAL 1 MONTH)
        """
        vendas_mes_anterior = conexao.select(sql_vendas_mes_anterior, (id_vendedor,))
        
        # Vendas por mês (últimos 6 meses)
        sql_vendas_ultimos_meses = """
            SELECT DATE_FORMAT(c.data_compra, '%Y-%m') as mes, 
                   COUNT(*) as total_vendas, 
                   COALESCE(SUM(c.total), 0) as faturamento
            FROM compras_tt c
            JOIN produtos_tt p ON c.id_produto = p.id_produto
            WHERE p.criado_por_id = %s AND c.status = 'entregue'
            AND c.data_compra >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
            GROUP BY DATE_FORMAT(c.data_compra, '%Y-%m')
            ORDER BY mes ASC
        """
        vendas_ultimos_meses = conexao.select(sql_vendas_ultimos_meses, (id_vendedor,))
        
        # Top 5 produtos mais vendidos
        sql_top_produtos = """
            SELECT p.nome, COUNT(c.id_compra) as total_vendas, SUM(c.quantidade) as quantidade_vendida,
                   COALESCE(SUM(c.total), 0) as faturamento
            FROM produtos_tt p
            JOIN compras_tt c ON p.id_produto = c.id_produto
            WHERE p.criado_por_id = %s AND c.status = 'entregue'
            GROUP BY p.id_produto
            ORDER BY total_vendas DESC
            LIMIT 5
        """
        top_produtos = conexao.select(sql_top_produtos, (id_vendedor,))
        
        conexao.close()
        
        total_vendas_mes = int(vendas_mes[0][0]) if vendas_mes and vendas_mes[0][0] else 0
        faturamento_mes = float(vendas_mes[0][1]) if vendas_mes and vendas_mes[0][1] else 0
        total_vendas_anterior = int(vendas_mes_anterior[0][0]) if vendas_mes_anterior and vendas_mes_anterior[0][0] else 0
        
        # Calcular variação percentual
        variacao = 0
        if total_vendas_anterior > 0:
            variacao = ((total_vendas_mes - total_vendas_anterior) / total_vendas_anterior) * 100
        
        return jsonify({
            "vendas_mes": total_vendas_mes,
            "faturamento_mes": faturamento_mes,
            "faturamento_mes_formatado": f"{faturamento_mes:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            "variacao_percentual": round(variacao, 1),
            "vendas_ultimos_meses": [
                {
                    "mes": vm[0],
                    "total_vendas": vm[1],
                    "faturamento": float(vm[2])
                } for vm in vendas_ultimos_meses
            ],
            "top_produtos": [
                {
                    "nome": tp[0],
                    "total_vendas": tp[1],
                    "quantidade_vendida": tp[2],
                    "faturamento": float(tp[3])
                } for tp in top_produtos
            ]
        })
    
    except Exception as err:
        return jsonify({"erro": str(err)}), 500


@rotas_produto.route('/vendedor/api/dashboard')
def vendedor_api_dashboard():
    """Retorna dados do dashboard no formato esperado pelo frontend."""
    if not _admin_autenticada():
        return jsonify({"erro": "Não autorizado"}), 401

    try:
        conexao = ConexaoBD()
        id_vendedor = _garantir_vendedor_admin(conexao)

        sql_totais = """
            SELECT
                COUNT(*) AS total_produtos,
                COALESCE(SUM(estoque), 0) AS total_estoque
            FROM produtos_tt
            WHERE criado_por_id = %s
        """
        totais = conexao.select(sql_totais, (id_vendedor,))

        sql_vendas = """
            SELECT
                COUNT(*) AS total_vendas,
                COALESCE(SUM(c.total), 0) AS receita_total
            FROM compras_tt c
            JOIN produtos_tt p ON c.id_produto = p.id_produto
            WHERE p.criado_por_id = %s
              AND c.status = 'entregue'
        """
        vendas_gerais = conexao.select(sql_vendas, (id_vendedor,))

        sql_notificacoes_nao_lidas = """
            SELECT COUNT(*)
            FROM notificacoes_tt
            WHERE id_vendedor = %s AND lida = 0
        """
        notificacoes_nao_lidas = conexao.select(sql_notificacoes_nao_lidas, (id_vendedor,))

        has_cr_dash = table_has_column(conexao, "compras_tt", "codigo_rastreio")
        sql_vr = """
            SELECT
                c.id_compra,
                p.nome,
                c.quantidade,
                c.total,
                c.status,
                c.metodo_pagamento,
                c.data_compra
        """
        if has_cr_dash:
            sql_vr += ", c.codigo_rastreio"
        sql_vr += """
            FROM compras_tt c
            JOIN produtos_tt p ON c.id_produto = p.id_produto
            WHERE p.criado_por_id = %s
            ORDER BY c.data_compra DESC
            LIMIT 10
        """
        vendas_recentes = conexao.select(sql_vr, (id_vendedor,))

        sql_estoque_baixo = """
            SELECT id_produto, nome, estoque
            FROM produtos_tt
            WHERE criado_por_id = %s
              AND estoque < 10
            ORDER BY estoque ASC, nome ASC
            LIMIT 10
        """
        estoque_baixo = conexao.select(sql_estoque_baixo, (id_vendedor,))

        conexao.close()

        totais_row = totais[0] if totais else (0, 0)
        vendas_row = vendas_gerais[0] if vendas_gerais else (0, 0)
        notif_row = notificacoes_nao_lidas[0] if notificacoes_nao_lidas else (0,)

        return jsonify({
            "total_produtos": int(totais_row[0] or 0),
            "total_estoque": int(totais_row[1] or 0),
            "total_vendas": int(vendas_row[0] or 0),
            "receita_total": float(vendas_row[1] or 0),
            "notificacoes_nao_lidas": int(notif_row[0] or 0),
            "vendas_recentes": [
                {
                    "id": venda[0],
                    "produto": venda[1],
                    "quantidade": int(venda[2] or 0),
                    "total": float(venda[3] or 0),
                    "status": venda[4] or "pendente",
                    "metodo": venda[5] or "-",
                    "data": venda[6].strftime('%d/%m/%Y %H:%M') if venda[6] else "-",
                    "codigo_rastreio": (venda[7] or "") if has_cr_dash and len(venda) > 7 else "",
                } for venda in vendas_recentes
            ],
            "estoque_baixo": [
                {
                    "id": produto[0],
                    "nome": produto[1],
                    "estoque": int(produto[2] or 0)
                } for produto in estoque_baixo
            ]
        })
    except Exception as err:
        return jsonify({"erro": str(err)}), 500


@rotas_produto.route('/vendedor/api/produtos')
def vendedor_api_produtos():
    """Lista produtos do vendedor no formato esperado pelo frontend."""
    if not _admin_autenticada():
        return jsonify({"erro": "Não autorizado"}), 401

    try:
        conexao = ConexaoBD()
        id_vendedor = _garantir_vendedor_admin(conexao)

        sql = """
            SELECT p.id_produto, p.nome, p.descricao, p.categoria_id, p.preco, p.estoque, p.imagem, p.verificado,
                   c.nome as categoria
            FROM produtos_tt p
            LEFT JOIN categorias_produtos_tt c ON p.categoria_id = c.id_categoria
            WHERE p.criado_por_id = %s
            ORDER BY p.criado_em DESC
        """
        produtos = conexao.select(sql, (id_vendedor,))
        conexao.close()

        return jsonify([
            {
                "id": produto[0],
                "nome": produto[1],
                "descricao": produto[2] or "",
                "categoria_id": int(produto[3]) if produto[3] is not None else None,
                "preco": float(produto[4] or 0),
                "estoque": int(produto[5] or 0),
                "imagem": _montar_url_imagem_produto(produto[6]),
                "verificado": bool(produto[7]),
                "categoria": produto[8] or "Sem categoria"
            } for produto in produtos
        ])
    except Exception as err:
        return jsonify({"erro": str(err)}), 500


@rotas_produto.route('/vendedor/api/notificacoes')
def vendedor_api_notificacoes():
    """Lista notificações no formato esperado pelo frontend."""
    if not _admin_autenticada():
        return jsonify({"erro": "Não autorizado"}), 401

    try:
        conexao = ConexaoBD()
        id_vendedor = session.get('vendedor_id')

        sql = """
            SELECT id_notificacao, mensagem, data_envio, lida
            FROM notificacoes_tt
            WHERE id_vendedor = %s
            ORDER BY data_envio DESC
            LIMIT 50
        """
        notificacoes = conexao.select(sql, (id_vendedor,))
        conexao.close()

        return jsonify([
            {
                "id": notif[0],
                "titulo": "Nova atualização",
                "mensagem": notif[1] or "",
                "data": notif[2].strftime('%d/%m/%Y %H:%M') if notif[2] else "-",
                "lida": bool(notif[3])
            } for notif in notificacoes
        ])
    except Exception as err:
        return jsonify({"erro": str(err)}), 500


@rotas_produto.route('/vendedor/api/notificacoes/marcar_lida', methods=['POST'])
def vendedor_api_marcar_notificacao_lida():
    """Marca uma notificação como lida (compatibilidade com frontend)."""
    if not _admin_autenticada():
        return jsonify({"erro": "Não autorizado"}), 401

    try:
        data = request.get_json(silent=True) or {}
        id_notificacao = data.get('id_notificacao')
        if not id_notificacao:
            return jsonify({"erro": "id_notificacao é obrigatório"}), 400

        id_vendedor = session.get('vendedor_id')
        conexao = ConexaoBD()
        sql = "UPDATE notificacoes_tt SET lida = 1 WHERE id_notificacao = %s AND id_vendedor = %s"
        conexao.update(sql, (id_notificacao, id_vendedor))
        conexao.close()

        return jsonify({"success": True, "mensagem": "Notificação marcada como lida"})
    except Exception as err:
        return jsonify({"erro": str(err)}), 500


@rotas_produto.route('/vendedor/api/notificacoes/marcar_todas_lidas', methods=['POST'])
def vendedor_api_marcar_todas_notificacoes_lidas():
    """Marca todas notificações como lidas (compatibilidade com frontend)."""
    if not _admin_autenticada():
        return jsonify({"erro": "Não autorizado"}), 401

    try:
        id_vendedor = session.get('vendedor_id')
        conexao = ConexaoBD()
        sql = "UPDATE notificacoes_tt SET lida = 1 WHERE id_vendedor = %s AND lida = 0"
        conexao.update(sql, (id_vendedor,))
        conexao.close()

        return jsonify({"success": True, "mensagem": "Notificações atualizadas"})
    except Exception as err:
        return jsonify({"erro": str(err)}), 500


@rotas_produto.route('/vendedor/produto/novo', methods=['POST'])
def vendedor_api_novo_produto():
    """Cria produto via JSON (compatibilidade com frontend)."""
    if not _admin_autenticada():
        return jsonify({"erro": "Não autorizado"}), 401

    try:
        data = request.get_json(silent=True) or {}
        nome = data.get('nome')
        descricao = data.get('descricao')
        categoria_id = data.get('categoria_id')
        preco = data.get('preco')
        estoque = data.get('estoque')
        imagem = _normalizar_imagem_produto(data.get('imagem'))

        if not all([nome, descricao, categoria_id is not None, preco is not None, estoque is not None]):
            return jsonify({"success": False, "erro": "Preencha todos os campos obrigatórios"}), 400

        conexao = ConexaoBD()
        _inserir_produto_admin(conexao, nome, descricao, categoria_id, preco, estoque, imagem)
        conexao.close()

        return jsonify({"success": True, "mensagem": "Produto adicionado com sucesso!"}), 200
    except ValueError as err:
        return jsonify({"success": False, "erro": str(err)}), 400
    except Exception as err:
        return jsonify({"success": False, "erro": str(err)}), 500


@rotas_produto.route('/vendedor/produto/editar/<int:id_produto>', methods=['PUT'])
def vendedor_api_editar_produto(id_produto):
    """Edita produto via JSON (compatibilidade com frontend)."""
    if not _admin_autenticada():
        return jsonify({"erro": "Não autorizado"}), 401

    try:
        data = request.get_json(silent=True) or {}
        nome = data.get('nome')
        descricao = data.get('descricao')
        categoria_id = data.get('categoria_id')
        preco = data.get('preco')
        estoque = data.get('estoque')
        imagem = _normalizar_imagem_produto(data.get('imagem'))

        if not all([nome, descricao, categoria_id is not None, preco is not None, estoque is not None]):
            return jsonify({"success": False, "erro": "Preencha todos os campos obrigatórios"}), 400

        id_vendedor = session.get('vendedor_id')
        conexao = ConexaoBD()

        verifica = conexao.select(
            "SELECT id_produto FROM produtos_tt WHERE id_produto = %s AND criado_por_id = %s",
            (id_produto, id_vendedor)
        )
        if not verifica:
            conexao.close()
            return jsonify({"success": False, "erro": "Produto não encontrado"}), 404

        sql = """
            UPDATE produtos_tt
            SET nome = %s, descricao = %s, categoria_id = %s, preco = %s, estoque = %s, imagem = %s
            WHERE id_produto = %s AND criado_por_id = %s
        """
        conexao.update(
            sql,
            (nome, descricao, int(categoria_id), float(preco), int(estoque), imagem, id_produto, id_vendedor)
        )
        conexao.close()

        return jsonify({"success": True, "mensagem": "Produto atualizado com sucesso!"}), 200
    except Exception as err:
        return jsonify({"success": False, "erro": str(err)}), 500


@rotas_produto.route('/vendedor/produto/deletar/<int:id_produto>', methods=['DELETE'])
def vendedor_api_deletar_produto(id_produto):
    """Remove produto (compatibilidade com frontend)."""
    if not _admin_autenticada():
        return jsonify({"erro": "Não autorizado"}), 401

    try:
        id_vendedor = session.get('vendedor_id')
        conexao = ConexaoBD()

        verifica = conexao.select(
            "SELECT id_produto FROM produtos_tt WHERE id_produto = %s AND criado_por_id = %s",
            (id_produto, id_vendedor)
        )
        if not verifica:
            conexao.close()
            return jsonify({"success": False, "erro": "Produto não encontrado"}), 404

        tem_vendas = conexao.select(
            "SELECT id_compra FROM compras_tt WHERE id_produto = %s AND status != 'cancelado' LIMIT 1",
            (id_produto,)
        )
        if tem_vendas:
            conexao.close()
            return jsonify({"success": False, "erro": "Não é possível excluir um produto que já possui vendas"}), 400

        conexao.delete("DELETE FROM produtos_tt WHERE id_produto = %s AND criado_por_id = %s", (id_produto, id_vendedor))
        conexao.close()

        return jsonify({"success": True, "mensagem": "Produto excluído com sucesso!"}), 200
    except Exception as err:
        return jsonify({"success": False, "erro": str(err)}), 500


@rotas_produto.route('/vendedor/logout')
def vendedor_logout():
    """Logout do vendedor"""
    session.pop('vendedor_logado', None)
    session.pop('vendedor_id', None)
    session.pop('vendedor_nome', None)
    session.pop('vendedor_email', None)
    session.pop('is_admin', None)
    return redirect(url_for('produto.home'))