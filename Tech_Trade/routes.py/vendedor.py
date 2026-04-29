

# ------------------- SISTEMA VENDEDOR -------------------

@rotas_produto.route('/vendedor/login', methods=['GET', 'POST'])
def vendedor_login():
    """Login específico para vendedores"""
    try:
        if request.method == 'POST':
            email = request.form.get('email')
            senha = request.form.get('senha')
            
            if not email or not senha:
                return render_template('vendedor_login.html', erro="Preencha todos os campos.")
            
            conexao = ConexaoBD()
            sql = """
                SELECT id_vendedor, nome, email, senha, aprovado, data_cadastro 
                FROM vendedores_tt 
                WHERE email = %s
            """
            vendedor = conexao.select(sql, (email,))
            conexao.close()
            
            if vendedor and check_password_hash(vendedor[0][3], senha):
                if not vendedor[0][4]:
                    flash("Sua conta de vendedor aguarda aprovação.", "erro")
                    return render_template('vendedor_login.html', erro="Aguardando aprovação do administrador.")
                
                session['vendedor_logado'] = True
                session['vendedor_id'] = vendedor[0][0]
                session['vendedor_nome'] = vendedor[0][1]
                session['vendedor_email'] = vendedor[0][2]
                
                return redirect(url_for('produto.vendedor_dashboard'))
            else:
                return render_template('vendedor_login.html', erro="E-mail ou senha incorretos.")
        
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
            
            if senha != confirmar_senha:
                return render_template('vendedor_cadastro.html', erro="As senhas não conferem.")
            
            if len(senha) < 6:
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
    if not session.get('vendedor_logado'):
        return redirect(url_for('produto.vendedor_login'))
    
    try:
        conexao = ConexaoBD()
        id_vendedor = session.get('vendedor_id')
        
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
        
        return render_template('vendedor_dashboard.html', 
                             stats=stats,
                             produtos=produtos,
                             ultimas_vendas=ultimas_vendas, 
                             notificacoes=notificacoes,
                             categorias=categorias,
                             vendedor_nome=session.get('vendedor_nome'))
    
    except Exception as err:
        return render_template('vendedor_dashboard.html', erro=str(err), vendedor_nome=session.get('vendedor_nome'))


@rotas_produto.route('/vendedor/produtos/adicionar', methods=['POST'])
def vendedor_adicionar_produto():
    """Adicionar novo produto"""
    if not session.get('vendedor_logado'):
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
            import os
            extensao = imagem.filename.rsplit('.', 1)[-1].lower()
            nome_imagem = secure_filename(f"prod_{id_vendedor}_{int(datetime.now().timestamp())}.{extensao}")
            caminho = os.path.join('src/static/tech_trade_imagens', nome_imagem)
            imagem.save(caminho)
        
        conexao = ConexaoBD()
        sql = """
            INSERT INTO produtos_tt (nome, descricao, categoria_id, preco, estoque, 
                                   criado_por, criado_por_id, imagem, verificado, criado_em)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, NOW())
        """
        conexao.insert(sql, (nome, descricao, categoria_id, preco, estoque, 
                            vendedor_nome, id_vendedor, nome_imagem))
        conexao.close()
        
        return jsonify({"mensagem": "Produto adicionado com sucesso!"}), 200
    
    except Exception as err:
        return jsonify({"erro": str(err)}), 500


@rotas_produto.route('/vendedor/produto/buscar/<int:id_produto>')
def vendedor_buscar_produto(id_produto):
    """Buscar dados de um produto para edição"""
    if not session.get('vendedor_logado'):
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
    if not session.get('vendedor_logado'):
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
    if not session.get('vendedor_logado'):
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
    if not session.get('vendedor_logado'):
        return jsonify({"erro": "Não autorizado"}), 401
    
    try:
        conexao = ConexaoBD()
        id_vendedor = session.get('vendedor_id')
        
        sql = """
            SELECT c.id_compra, p.nome as produto_nome, c.quantidade, c.total, 
                   c.metodo_pagamento, c.status, c.data_compra, c.endereco_entrega,
                   cl.nome as cliente_nome, cl.email as cliente_email, cl.telefone as cliente_telefone
            FROM compras_tt c
            JOIN produtos_tt p ON c.id_produto = p.id_produto
            JOIN clientes_tt cl ON c.id_cliente = cl.id_cliente
            WHERE p.criado_por_id = %s
            ORDER BY c.data_compra DESC
        """
        pedidos = conexao.select(sql, (id_vendedor,))
        conexao.close()
        
        pedidos_json = []
        for p in pedidos:
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
                "cliente_telefone": p[10] or 'Não informado'
            })
        
        return jsonify(pedidos_json)
    
    except Exception as err:
        return jsonify({"erro": str(err)}), 500


@rotas_produto.route('/vendedor/pedidos/atualizar_status/<int:id_pedido>', methods=['POST'])
def vendedor_atualizar_status_pedido(id_pedido):
    """Atualizar status do pedido"""
    if not session.get('vendedor_logado'):
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
        
        status_validos = ['pendente', 'pago', 'processando', 'enviado', 'entregue', 'cancelado']
        if status not in status_validos:
            conexao.close()
            return jsonify({"erro": "Status inválido"}), 400
        
        sql = "UPDATE compras_tt SET status = %s WHERE id_compra = %s"
        conexao.update(sql, (status, id_pedido))
        conexao.close()
        
        return jsonify({"mensagem": f"Status do pedido atualizado para {status} com sucesso!"}), 200
    
    except Exception as err:
        return jsonify({"erro": str(err)}), 500


@rotas_produto.route('/vendedor/notificacoes/marcar_lida/<int:id_notificacao>', methods=['POST'])
def vendedor_marcar_notificacao_lida(id_notificacao):
    """Marcar notificação como lida"""
    if not session.get('vendedor_logado'):
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
    if not session.get('vendedor_logado'):
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


@rotas_produto.route('/vendedor/logout')
def vendedor_logout():
    """Logout do vendedor"""
    session.pop('vendedor_logado', None)
    session.pop('vendedor_id', None)
    session.pop('vendedor_nome', None)
    session.pop('vendedor_email', None)
    return redirect(url_for('produto.home'))