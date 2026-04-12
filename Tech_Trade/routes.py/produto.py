from datetime import datetime, timedelta
from src.utils.bd import ConexaoBD
from flask import Blueprint, jsonify, render_template, request, abort, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import hashlib
import secrets

rotas_produto = Blueprint('produto', __name__)

# ------------------- RENDERIZAÇÃO DE PÁGINAS -------------------

@rotas_produto.route('/')
def home():
    """Página inicial"""
    return render_template('home.html')

# ------------------- LOGIN DE CLIENTE -------------------

@rotas_produto.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if request.method == 'POST':
            email = request.form.get('email')
            senha = request.form.get('senha')

            conexao = ConexaoBD()
            sql = "SELECT id_cliente, nome, senha FROM clientes_tt WHERE email = %s"
            usuario = conexao.select(sql, (email,))
            conexao.close()

            if usuario and check_password_hash(usuario[0][2], senha):
                session['usuario_logado'] = True
                session['usuario_nome'] = usuario[0][1]
                session['usuario_id'] = usuario[0][0]
                return redirect(url_for('produto.renderizar_produtos'))
            else:
                erro = "E-mail ou senha incorretos."
                return render_template('login.html', erro=erro)

        return render_template('login.html')

    except Exception as err:
        abort(500)

# ------------------- CADASTRO DE CLIENTE -------------------

@rotas_produto.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    try:
        if request.method == 'POST':
            nome = request.form.get('nome')
            email = request.form.get('email')
            senha = request.form.get('senha')
            telefone = request.form.get('telefone')

            if not nome or not email or not senha or not telefone:
                return render_template('cadastro.html', erro="Preencha todos os campos obrigatórios.")

            conexao = ConexaoBD()

            # Verifica se já existe
            sql_verifica = "SELECT id_cliente FROM clientes_tt WHERE email = %s"
            existente = conexao.select(sql_verifica, (email,))
            if existente:
                conexao.close()
                return render_template('cadastro.html', erro="E-mail já cadastrado.")

            # Inserir cliente
            hash_senha = generate_password_hash(senha)
            sql_insert = """
                INSERT INTO clientes_tt (nome, email, senha, telefone, criado_em)
                VALUES (%s, %s, %s, %s, NOW())
            """
            conexao.insert(sql_insert, (nome, email, hash_senha, telefone))

            sql_busca = "SELECT id_cliente FROM clientes_tt WHERE email = %s"
            usuario = conexao.select(sql_busca, (email,))
            conexao.close()

            session['usuario_logado'] = True
            session['usuario_nome'] = nome
            session['usuario_id'] = usuario[0][0]


            return redirect(url_for('produto.renderizar_produtos'))

        return render_template('cadastro.html')

    except Exception as err:
        return render_template('cadastro.html', erro="Erro ao cadastrar.")
# ------------------- RECUPERAÇÃO DE SENHA -------------------

@rotas_produto.route('/esqueceu_senha', methods=['GET', 'POST'])
def esqueceu_senha():
    """Página para solicitar recuperação de senha"""
    try:
        if request.method == 'POST':
            email = request.form.get('email')
            
            if not email:
                return render_template('esqueceu_senha.html', erro="Por favor, informe seu e-mail.")
            
            conexao = ConexaoBD()
            
            # Verificar se o e-mail existe
            sql = "SELECT id_cliente, nome FROM clientes_tt WHERE email = %s"
            usuario = conexao.select(sql, (email,))
            
            if usuario:
                
                token = secrets.token_urlsafe(32)
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                expiracao = datetime.now() + timedelta(hours=1)
                
                # Salvar token no banco
                sql_token = """
                    INSERT INTO recuperacao_senha_tt (id_cliente, token, expiracao, usado)
                    VALUES (%s, %s, %s, 0)
                """
                conexao.insert(sql_token, (usuario[0][0], token_hash, expiracao))
                
                # Gerar link de recuperação
                link_recuperacao = url_for('produto.redefinir_senha', token=token, _external=True)
                
                
                conexao.close()
                
                # RETORNAR APENAS O LINK DE DEBUG (SEM MENSAGEM DE SUCESSO)
                return render_template('esqueceu_senha.html', 
                                     link_debug=link_recuperacao)
            else:
                conexao.close()
                # Por segurança, não informe se o e-mail não existe
                return render_template('esqueceu_senha.html', 
                                     mensagem="Se o e-mail estiver cadastrado, você receberá as instruções de recuperação.")
        
        return render_template('esqueceu_senha.html')
    
    except Exception as err:
        return render_template('esqueceu_senha.html', erro="Erro ao processar solicitação.")

@rotas_produto.route('/redefinir_senha/<token>', methods=['GET', 'POST'])
def redefinir_senha(token):
    """Página para redefinir a senha usando o token"""
    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        conexao = ConexaoBD()
        
        # Verificar se o token é válido e não expirou
        sql = """
            SELECT r.id_cliente, c.nome, r.expiracao
            FROM recuperacao_senha_tt r
            JOIN clientes_tt c ON r.id_cliente = c.id_cliente
            WHERE r.token = %s AND r.usado = 0
        """
        recuperacao = conexao.select(sql, (token_hash,))
        
        if not recuperacao:
            conexao.close()
            return render_template('redefinir_senha.html', 
                                 erro="Token inválido ou já utilizado.")
        
        id_cliente = recuperacao[0][0]
        nome_cliente = recuperacao[0][1]
        expiracao = recuperacao[0][2]
        
        # Verificar se o token expirou
        if datetime.now() > expiracao:
            conexao.close()
            return render_template('redefinir_senha.html', 
                                 erro="Token expirado. Solicite uma nova recuperação.")
        
        if request.method == 'POST':
            nova_senha = request.form.get('nova_senha')
            confirmar_senha = request.form.get('confirmar_senha')
            
            if not nova_senha or not confirmar_senha:
                return render_template('login.html', 
                                     token=token,
                                     erro="Preencha todos os campos.")
            
            if nova_senha != confirmar_senha:
                return render_template('login.html', 
                                     token=token,
                                     erro="As senhas não conferem.")
            
            # Atualizar a senha
            hash_senha = generate_password_hash(nova_senha)
            sql_update = "UPDATE clientes_tt SET senha = %s WHERE id_cliente = %s"
            conexao.update(sql_update, (hash_senha, id_cliente))
            
            conexao.commit()
            
            # Marcar token como usado
            sql_usar_token = "UPDATE recuperacao_senha_tt SET usado = 1 WHERE token = %s"
            conexao.insert(sql_usar_token, (token_hash,))
            
            conexao.close()
            
            return render_template('login.html', 
                                 mensagem="Senha redefinida com sucesso!",
                                 sucesso=True)
        
        conexao.close()
        
        return render_template('login.html', 
                             token=token,
                             nome_cliente=nome_cliente)
    
    except Exception as err:
        return render_template('login.html', erro="Erro ao processar solicitação.")
# ------------------- RENDERIZAÇÃO DE PÁGINAS -------------------       

@rotas_produto.route("/produtos")
def renderizar_produtos():
    try:
        return render_template("produtos.html")
    except Exception as err:
        abort(404)

# ------------------- CONSULTAS AO BANCO -------------------

@rotas_produto.get("/techtrade/categorias")
def consultar_categorias_produtos():
    """Retorna as categorias dos produtos"""
    try:
        conexao = ConexaoBD()
        categorias = conexao.select("SELECT id_categoria, nome FROM categorias_produtos_tt")
        conexao.close()
        return jsonify(categorias)
    except Exception as err:
        erro = str(err).replace("'", '"')
        return jsonify({"erro": erro}), 500
#............................................................................................................
@rotas_produto.get("/techtrade/produtos/registros")
def consultar_produtos():
    """Retorna a lista de produtos"""
    try:
        conexao_bd = ConexaoBD()
        retorno_bd = conexao_bd.select("""
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
                p.verificado_por,
                p.verificado_em
            FROM produtos_tt p
            LEFT JOIN categorias_produtos_tt c ON p.categoria_id = c.id_categoria
            ORDER BY p.id_produto DESC
        """)
        conexao_bd.close()

        # --- Funções auxiliares ---
        def formata_data(data):
            if isinstance(data, datetime):
                return data.strftime('%d/%m/%Y')
            return str(data) if data else ""

        def safe_float(x):
            try:
                return float(x) if x is not None else 0.0
            except (TypeError, ValueError):
                return 0.0

        def safe_int(x):
            try:
                return int(x) if x is not None else 0
            except (TypeError, ValueError):
                try:
                    return int(float(x))
                except Exception:
                    return 0

        # Imagens de placeholder por categoria
        def get_placeholder_image(categoria):
            placeholders = {
                'Celulares': 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80',
                'Computadores': 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80',
                'Tablets': 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80',
                'Periféricos': 'https://images.unsplash.com/photo-1593640408182-31c70c8268f5?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80',
                'Acessórios': 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80',
                'Games': 'https://images.unsplash.com/photo-1606813907291-d86efa9b94db?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80'
            }
            return placeholders.get(categoria, 'https://images.unsplash.com/photo-1556656793-08538906a9f8?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80')

        # --- Monta o JSON final ---
        json_produtos = []
        for row in retorno_bd:
            imagem = f"/static/tech_trade_imagens/{row[8]}" if row[8] else get_placeholder_image(row[3])
            
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
                "verificado": row[9] if len(row) > 9 else True,
                "verificado_por": row[10] or "",
                "verificado_em": formata_data(row[11]) if row[11] else ""
            })

        return jsonify({"json_produtos": json_produtos})

    except Exception as err:
        erro = str(err).replace("'", '"')
        return jsonify({"erro": erro}), 500

@rotas_produto.route('/techtrade/produtos/verificar', methods=['POST'])
def verificar_produto():
    """Marca um produto como verificado"""
    try:
        dados = request.get_json()
        id_produto = dados.get('id_produto')
        verificado = dados.get('verificado', True)
        verificado_por = dados.get('verificado_por', 'Sistema')
        verificacao_obs = dados.get('verificacao_obs', '')

        if not id_produto:
            return jsonify({"erro": "ID do produto é obrigatório"}), 400

        conexao = ConexaoBD()
        sql = """
            UPDATE produtos_tt
            SET verificado = %s,
                verificado_por = %s,
                verificado_em = NOW(),
                verificacao_obs = %s
            WHERE id_produto = %s
        """
        conexao.insert(sql, (1 if verificado else 0, verificado_por, verificacao_obs, id_produto))
        conexao.close()

        return jsonify({"mensagem": "Produto verificado com sucesso!"}), 200

    except Exception as e:
        return jsonify({"erro": str(e)}), 500


# ------------------- CONCLUIR COMPRA -------------------

@rotas_produto.route("/techtrade/produtos/checkout/<int:id_produto>", methods=["GET", "POST"])
def checkout(id_produto):
    try:
        conexao = ConexaoBD()
        
        # Buscar produto
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
        
        if not resultado or len(resultado) == 0:
            conexao.close()
            abort(404, "Produto não encontrado")

        # Extrair dados do produto
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
            "vendedor_id": p[8]
        }

        if request.method == "POST":
            metodo = request.form.get("metodo")
            endereco = request.form.get("endereco", "")
            observacoes = request.form.get("observacoes", "")
            
            if not metodo:
                conexao.close()
                return "Método de pagamento não selecionado.", 400

            # Registrar compra usando o novo sistema completo
            try:
                dados_compra = {
                    "id_produto": id_produto,
                    "metodo_pagamento": metodo,
                    "endereco_entrega": endereco,
                    "observacoes": observacoes
                }

                # Fechar conexão atual antes de fazer a requisição
                conexao.close()
                
                # Fazer requisição para a nova rota de compra completa
                import requests
                from flask import url_for
                
                # Criar uma requisição interna para a nova rota
                with rotas_produto.test_client() as client:
                    response = client.post(
                        '/techtrade/produtos/finalizar_compra_completa',
                        json=dados_compra,
                        headers={'Content-Type': 'application/json'}
                    )
                    
                    if response.status_code == 201:
                        data = response.get_json()
                        mensagem = f"Compra do produto '{produto['nome']}' realizada com sucesso via {metodo}!"
                        return render_template("confirmacao.html", 
                                                mensagem=mensagem, 
                                                produto=produto,
                                                metodo=metodo,
                                                now=datetime.now())
                    else:
                        erro = response.get_json().get('erro', 'Erro ao processar compra')
                        return f"Erro: {erro}", 400

            except Exception as e:
                if 'conexao' in locals():
                    conexao.close()
                return f"Erro ao processar compra: {str(e)}", 500

        # GET request - mostrar página de checkout
        conexao.close()
        return render_template("checkout.html", produto=produto)

    except Exception as err:
        if 'conexao' in locals():
            conexao.close()
        abort(500)

# ------------------- COMPROVANTE DE COMPRA -------------------

@rotas_produto.route("/comprovante/<int:id_produto>")
def comprovante_compra(id_produto):
    """Página dedicada para o comprovante de compra"""
    try:
        # Buscar dados reais do produto do banco
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
            "imagem": produto_db[0][4] or "default.jpg"
        }
        
        metodo = request.args.get('metodo', 'PIX')
        
        return render_template("comprovante.html", 
                             produto=produto,
                             metodo=metodo,
                             now=datetime.now(),
                             usuario_nome=session.get('usuario_nome', 'Cliente TechTrade'))
    except Exception as e:
        abort(500)

# ------------------- SISTEMA DE COMPRAS E NOTIFICAÇÕES -------------------

@rotas_produto.route("/techtrade/produtos/finalizar_compra_completa", methods=["POST"])
def finalizar_compra_completa():
    """Registra compra, atualiza estoque e notifica vendedor - VERSÃO CORRIGIDA"""
    try:
        if not session.get('usuario_logado'):
            return jsonify({"erro": "Usuário não logado"}), 401

        dados = request.get_json()
        
        id_produto = dados.get('id_produto')
        metodo_pagamento = dados.get('metodo_pagamento')
        endereco_entrega = dados.get('endereco_entrega', '')
        observacoes = dados.get('observacoes', '')

        if not all([id_produto, metodo_pagamento]):
            return jsonify({"erro": "Dados incompletos"}), 400

        id_cliente = session.get('usuario_id')
        quantidade = 1
        
        conexao = ConexaoBD()

        # 1. Buscar informações do produto e vendedor
        sql_produto = """
            SELECT p.preco, p.estoque, p.criado_por_id, p.nome, 
                   COALESCE(v.nome, 'Vendedor TechTrade') as vendedor_nome,
                   COALESCE(v.email, 'vendedor@techtrade.com') as vendedor_email
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
        email_vendedor = produto_info[0][5]
        total = preco_unitario * quantidade

        # 2. Verificar estoque
        if estoque_atual < quantidade:
            conexao.close()
            return jsonify({"erro": "Estoque insuficiente"}), 400

        # 3. Inserir compra no banco
        sql_compra = """
            INSERT INTO compras_tt 
            (id_cliente, id_produto, quantidade, preco_unitario, total, 
             metodo_pagamento, endereco_entrega, observacoes, status, data_compra)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pendente', NOW())
        """
        conexao.insert(sql_compra, (
            id_cliente, id_produto, quantidade, preco_unitario, total,
            metodo_pagamento, endereco_entrega, observacoes
        ))

        # 4. Atualizar estoque do produto
        sql_estoque = "UPDATE produtos_tt SET estoque = estoque - %s WHERE id_produto = %s"
        conexao.insert(sql_estoque, (quantidade, id_produto))

        # 5. Notificar vendedor (inserir na tabela de notificações)
        if id_vendedor:
            mensagem_notificacao = f" Nova venda! {nome_produto} vendido para o cliente via {metodo_pagamento}. Total: R$ {total:.2f}"
            
            sql_notificacao = """
                INSERT INTO notificacoes_tt (id_vendedor, mensagem, data_envio, lida)
                VALUES (%s, %s, NOW(), 0)
            """
            conexao.insert(sql_notificacao, (id_vendedor, mensagem_notificacao))
            

        conexao.close()

        # Armazenar dados da compra na sessão para a página de confirmação
        session['produto'] = {
            "id_produto": int(id_produto),
            "nome": nome_produto,
            "descricao": f"Descrição do {nome_produto}",
            "preco": preco_unitario,
            "imagem": "/static/tech_trade_imagens/default.jpg",
            "vendedor": nome_vendedor
        }
        session['mensagem'] = "Compra realizada com sucesso!"
        session['metodo'] = metodo_pagamento
        session['usuario_nome'] = session.get('usuario_nome', 'Cliente')

        return jsonify({
            "mensagem": "Compra realizada com sucesso!",
            "id_produto": id_produto,
            "nome_produto": nome_produto,
            "preco": preco_unitario,
            "metodo_pagamento": metodo_pagamento,
            "vendedor": nome_vendedor,
            "notificado": bool(id_vendedor)
        }), 201

    except Exception as err:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": str(err)}), 500


# ------------------- PÁGINA DE CONFIRMAÇÃO DE COMPRA -------------------

@rotas_produto.route("/confirmacao")
def confirmacao_compra():
    try:
        produto = session.get('produto')
        metodo = session.get('metodo', 'PIX')
        mensagem = session.get('mensagem', 'Compra realizada com sucesso!')

        if not produto:
            return redirect(url_for('produto.renderizar_produtos'))

        return render_template(
            "confirmacao.html",
            produto=produto,
            metodo=metodo,
            mensagem=mensagem,
            now=datetime.now(),
            usuario_nome=session.get('usuario_nome', 'Cliente TechTrade')
        )

    except Exception as e:
        return "Erro na confirmação", 500

# ------------------- PÁGINA DE SUPORTE DO COMPRADOR -------------------

@rotas_produto.route('/suporte_comprador')
def suporte_comprador():
    """Página de suporte e ajuda para compradores"""
    return render_template('suporte_comprador.html')