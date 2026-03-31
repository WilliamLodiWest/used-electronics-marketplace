from flask import Blueprint, jsonify, render_template, request, abort
from datetime import datetime
from src.utils.bd import ConexaoBD
from flask import Blueprint, jsonify, render_template, request, abort, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import hashlib


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
                print(f"✅ Login realizado por {usuario[0][1]}")
                return redirect(url_for('produto.renderizar_produtos'))
            else:
                erro = "E-mail ou senha incorretos."
                return render_template('login.html', erro=erro)

        return render_template('login.html')

    except Exception as err:
        print(f"❌ Erro ao processar login: {err}")
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

            # 🔥 BUSCAR ID DO CLIENTE
            sql_busca = "SELECT id_cliente FROM clientes_tt WHERE email = %s"
            usuario = conexao.select(sql_busca, (email,))
            conexao.close()

            # 🔥 SALVAR NA SESSION (CORREÇÃO PRINCIPAL)
            session['usuario_logado'] = True
            session['usuario_nome'] = nome
            session['usuario_id'] = usuario[0][0]

            print(f"✅ Cliente cadastrado: {nome}")

            return redirect(url_for('produto.renderizar_produtos'))

        return render_template('cadastro.html')

    except Exception as err:
        print(f"❌ Erro no cadastro: {err}")
        return render_template('cadastro.html', erro="Erro ao cadastrar.")

# ------------------- RENDERIZAÇÃO DE PÁGINAS -------------------       

@rotas_produto.route("/produtos")
def renderizar_produtos():
    try:
        return render_template("produtos.html")
    except Exception as err:
        print(f"Erro ao renderizar produtos: {err}")
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

@rotas_produto.get("/techtrade/produtos/registros")
def consultar_produtos():
    """Retorna a lista de produtos"""
    # try:
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

    # except Exception as err:
    #     erro = str(err).replace("'", '"')
    #     return jsonify({"erro": erro}), 500

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

# ------------------- PÁGINA DE CHECKOUT -------------------

@rotas_produto.route("/techtrade/produtos/checkout/<int:id_produto>")
def checkout_produto(id_produto):
    """Renderiza a página de checkout de um produto específico"""
    try:
        conexao = ConexaoBD()

        sql = """
            SELECT 
                p.id_produto,
                p.nome,
                p.descricao,
                p.preco,
                p.estoque,
                p.imagem,
                p.verificado,
                p.verificado_por,
                p.verificado_em,
                p.criado_por
            FROM produtos_tt p
            WHERE p.id_produto = %s
        """
        resultado = conexao.select(sql, (id_produto,))
        conexao.close()

        if not resultado or len(resultado) == 0:
            abort(404)

        # Extrai os dados
        p = resultado[0]

        produto = {
            "id_produto": p[0],
            "nome": p[1],
            "descricao": p[2],
            "preco": float(p[3]),
            "estoque": int(p[4]),
            "imagem": f"/static/tech_trade_imagens/{p[5]}" if p[5] else "/static/tech_trade_imagens/default.jpg",
            "verificado": bool(p[6]),
            "verificado_por": p[7] or "Sistema TechTrade",
            "verificado_em": p[8],
            "vendedor": p[9] or "Vendedor não informado"
        }

        return render_template("checkout.html", produto=produto)

    except Exception as err:
        print(f"❌ Erro ao carregar checkout: {err}")
        abort(500)

# ------------------- CADASTRO DE VENDEDORES -------------------

@rotas_produto.route('/api/vendedores', methods=['POST'])
def cadastrar_vendedor():
    try:
        dados = request.get_json()

        nome = dados.get('nome')
        email = dados.get('email')
        senha = dados.get('senha')
        meio_comunicacao = dados.get('meio_comunicacao')

        # --- Validação básica ---
        if not nome or not email or not senha or not meio_comunicacao:
            return jsonify({"erro": "Campos obrigatórios faltando"}), 400

        # --- Inserir no banco de dados ---
        conexao = ConexaoBD()
        sql = """
            INSERT INTO vendedores_tt (nome, email, senha, meio_comunicacao, criado_em)
            VALUES (%s, %s, %s, %s, NOW())
        """
        conexao.insert(sql, (nome, email, senha, meio_comunicacao))
        conexao.close()

        print(f"✅ Novo vendedor cadastrado: {nome} ({meio_comunicacao})")

        return jsonify({"mensagem": "Vendedor cadastrado com sucesso!"}), 201

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# ------------------- PÁGINA DE CADASTRO DE VENDEDOR -------------------

@rotas_produto.route('/cadastro_vendedor', methods=['GET', 'POST'])
def cadastro_vendedor():
    """Página de cadastro para vendedores"""
    try:
        if request.method == 'POST':
            nome = request.form.get('nome')
            email = request.form.get('email')
            senha = request.form.get('senha')
            telefone = request.form.get('telefone')
            meio_comunicacao = request.form.get('meio_comunicacao', 'email')

            if not nome or not email or not senha:
                return render_template('cadastro_vendedor.html', erro="Preencha todos os campos obrigatórios.")

            conexao = ConexaoBD()

            # Verifica se o e-mail já está cadastrado
            sql_verifica = "SELECT id_vendedor FROM vendedores_tt WHERE email = %s"
            existente = conexao.select(sql_verifica, (email,))
            if existente:
                conexao.close()
                return render_template('cadastro_vendedor.html', erro="E-mail já cadastrado. Faça login.")

            # Insere novo vendedor
            sql = """
                INSERT INTO vendedores_tt (nome, email, senha, telefone, meio_comunicacao, criado_em)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """
            conexao.insert(sql, (nome, email, senha, telefone, meio_comunicacao))
            conexao.close()

            print(f"✅ Novo vendedor cadastrado: {nome} ({email})")

            # Redireciona para login
            return redirect(url_for('produto.login_vendedor'))

        return render_template('cadastro_vendedor.html')

    except Exception as err:
        print(f"❌ Erro ao cadastrar vendedor: {err}")
        return render_template('cadastro_vendedor.html', erro="Erro ao cadastrar. Tente novamente mais tarde.")

# ------------------- CONCLUIR COMPRA -------------------

@rotas_produto.route("/techtrade/produtos/checkout/<int:id_produto>", methods=["GET", "POST"])
def checkout(id_produto):
    # try:
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
            print(f"❌ Erro ao registrar compra: {e}")
            if 'conexao' in locals():
                conexao.close()
            return f"Erro ao processar compra: {str(e)}", 500

    # GET request - mostrar página de checkout
    conexao.close()
    return render_template("checkout.html", produto=produto)

    # except Exception as err:
    #     print(f"❌ Erro no checkout: {err}")
    #     if 'conexao' in locals():
    #         conexao.close()
    #     abort(500)

# ------------------- LISTAR NOTIFICAÇÕES DO VENDEDOR -------------------

@rotas_produto.route("/vendedor/<int:id_vendedor>/notificacoes")
def listar_notificacoes(id_vendedor):
    try:
        conexao = ConexaoBD()
        sql = """
            SELECT mensagem, data_envio, lida
            FROM notificacoes_tt
            WHERE id_vendedor = %s
            ORDER BY data_envio DESC
        """
        notificacoes = conexao.select(sql, (id_vendedor,))
        conexao.close()

        return render_template("notificacoes.html", notificacoes=notificacoes)
    except Exception as e:
        print(f"Erro ao listar notificações: {e}")
        abort(500)

# =============================================================================
# ====================== NOVAS ROTAS PARA VENDEDORES ==========================
# =============================================================================

# ------------------- LOGIN DE VENDEDOR -------------------

@rotas_produto.route('/login_vendedor', methods=['GET', 'POST'])
def login_vendedor():
    try:
        if request.method == 'POST':
            email = request.form.get('email')
            senha = request.form.get('senha')

            conexao = ConexaoBD()
            sql = "SELECT id_vendedor, nome, senha, email FROM vendedores_tt WHERE email = %s"
            vendedor = conexao.select(sql, (email,))
            conexao.close()

            if vendedor and vendedor[0][2] == senha:  # Em produção, use check_password_hash
                session['vendedor_logado'] = True
                session['vendedor_nome'] = vendedor[0][1]
                session['vendedor_id'] = vendedor[0][0]
                session['vendedor_email'] = vendedor[0][3]
                print(f"✅ Login de vendedor realizado por {vendedor[0][1]}")
                return redirect(url_for('produto.area_vendedor'))
            else:
                erro = "E-mail ou senha incorretos."
                return render_template('login_vendedor.html', erro=erro)

        return render_template('login_vendedor.html')

    except Exception as err:
        print(f"❌ Erro ao processar login do vendedor: {err}")
        abort(500)

# ------------------- ÁREA DO VENDEDOR -------------------
@rotas_produto.route('/area_vendedor')
def area_vendedor():
    if 'vendedor_id' not in session:
        return redirect('/login_vendedor')
    
    vendedor_id = session['vendedor_id']
    vendedor_nome = session.get('vendedor_nome', 'Vendedor')
    
    # Buscar vendas do vendedor
    try:
        conn = sqlite3.connect('tech_trade.db')
        cursor = conn.cursor()
        
        # Verificar se a tabela vendas existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vendas'")
        tabela_existe = cursor.fetchone()
        
        if not tabela_existe:
            vendas = []
            total_vendas = 0
            mensagem = "Tabela de vendas não existe. <a href='/criar_tabela_vendas'>Criar tabela</a>"
        else:
            # Buscar vendas
            cursor.execute('''
                SELECT v.*, c.nome as cliente_nome, p.nome as produto_nome, p.preco
                FROM vendas v
                JOIN clientes c ON v.cliente_id = c.id
                JOIN produtos p ON v.produto_id = p.id
                WHERE v.vendedor_id = ?
                ORDER BY v.data_venda DESC
            ''', (vendedor_id,))
            
            vendas = cursor.fetchall()
            
            # Contar total de vendas
            cursor.execute('SELECT COUNT(*) FROM vendas WHERE vendedor_id = ?', (vendedor_id,))
            total_vendas = cursor.fetchone()[0]
            mensagem = None
        
        conn.close()
        
    except Exception as e:
        print(f"Erro ao buscar vendas: {e}")
        vendas = []
        total_vendas = 0
        mensagem = f"Erro ao carregar vendas: {e}"
    
    return render_template('area_vendedor.html', 
                         vendedor_nome=vendedor_nome,
                         vendas=vendas,
                         total_vendas=total_vendas,
                         mensagem=mensagem)
# ------------------- VISUALIZAR COMPRAS DO VENDEDOR -------------------

@rotas_produto.route('/vendedor/compras')
def compras_vendedor():
    """Página para vendedor visualizar compras dos clientes - VERSÃO CORRIGIDA"""
    try:
        if not session.get('vendedor_logado'):
            return redirect(url_for('produto.login_vendedor'))

        vendedor_id = session.get('vendedor_id')
        vendedor_nome = session.get('vendedor_nome')
        
        print(f"🔍 Buscando compras para o vendedor ID: {vendedor_id}")
        
        conexao = ConexaoBD()
        
        # CONSULTA CORRIGIDA - Buscar produtos que pertencem ao vendedor
        sql_produtos_vendedor = "SELECT id_produto FROM produtos_tt WHERE criado_por_id = %s"
        produtos_vendedor = conexao.select(sql_produtos_vendedor, (vendedor_id,))
        
        if not produtos_vendedor:
            print("ℹ️ Nenhum produto encontrado para este vendedor")
            conexao.close()
            return render_template('compras_vendedor.html', 
                                 vendedor_nome=vendedor_nome,
                                 compras=[])
        
        # Extrair IDs dos produtos
        ids_produtos = [str(prod[0]) for prod in produtos_vendedor]
        placeholders = ','.join(['%s'] * len(ids_produtos))
        
        # Buscar compras dos produtos deste vendedor
        sql_compras = f"""
            SELECT 
                c.id_compra,
                c.id_cliente,
                COALESCE(cli.nome, 'Cliente') as cliente_nome,
                COALESCE(cli.email, 'Email não informado') as cliente_email,
                COALESCE(cli.telefone, 'Telefone não informado') as cliente_telefone,
                c.id_produto,
                COALESCE(p.nome, 'Produto') as produto_nome,
                p.imagem as produto_imagem,
                COALESCE(c.quantidade, 1) as quantidade,
                COALESCE(c.preco_unitario, 0) as preco_unitario,
                COALESCE(c.total, 0) as total,
                COALESCE(c.metodo_pagamento, 'PIX') as metodo_pagamento,
                COALESCE(c.status, 'pendente') as status,
                COALESCE(c.data_compra, NOW()) as data_compra,
                COALESCE(c.endereco_entrega, 'Endereço a combinar') as endereco_entrega,
                COALESCE(c.observacoes, 'Nenhuma observação') as observacoes
            FROM compras_tt c
            INNER JOIN produtos_tt p ON c.id_produto = p.id_produto
            LEFT JOIN clientes_tt cli ON c.id_cliente = cli.id_cliente
            WHERE c.id_produto IN ({placeholders})
            ORDER BY c.data_compra DESC
        """
        
        print(f"📋 Executando SQL para {len(ids_produtos)} produtos do vendedor")
        compras = conexao.select(sql_compras, tuple(ids_produtos))
        print(f"✅ Compras encontradas: {len(compras)}")
        
        conexao.close()

        # Formatar compras
        compras_formatadas = []
        for compra in compras:
            # Tratar data
            if compra[13]:
                if isinstance(compra[13], datetime):
                    data_formatada = compra[13].strftime('%d/%m/%Y %H:%M')
                else:
                    data_formatada = str(compra[13])
            else:
                data_formatada = 'Data não informada'
            
            # Tratar imagem do produto
            imagem_produto = compra[7]
            if imagem_produto and not imagem_produto.startswith('http'):
                imagem_url = f"/static/tech_trade_imagens/{imagem_produto}"
            else:
                imagem_url = imagem_produto or "/static/tech_trade_imagens/default.jpg"
            
            compra_formatada = {
                'id_compra': compra[0],
                'id_cliente': compra[1],
                'cliente_nome': compra[2],
                'cliente_email': compra[3],
                'cliente_telefone': compra[4],
                'id_produto': compra[5],
                'produto_nome': compra[6],
                'produto_imagem': imagem_url,
                'quantidade': compra[8],
                'preco_unitario': float(compra[9]),
                'total': float(compra[10]),
                'metodo_pagamento': compra[11],
                'status': compra[12],
                'data_compra': data_formatada,
                'endereco_entrega': compra[14],
                'observacoes': compra[15]
            }
            compras_formatadas.append(compra_formatada)

        print(f"🎉 Total de compras formatadas: {len(compras_formatadas)}")
        
        return render_template('compras_vendedor.html', 
                             vendedor_nome=vendedor_nome,
                             compras=compras_formatadas)

    except Exception as err:
        print(f"❌ ERRO ao carregar compras do vendedor: {err}")
        import traceback
        traceback.print_exc()
        
        return render_template('compras_vendedor.html', 
                             vendedor_nome=session.get('vendedor_nome'),
                             compras=[])

# ------------------- LOGOUT VENDEDOR -------------------

@rotas_produto.route('/logout_vendedor')
def logout_vendedor():
    """Faz logout do vendedor"""
    session.pop('vendedor_logado', None)
    session.pop('vendedor_id', None)
    session.pop('vendedor_nome', None)
    session.pop('vendedor_email', None)
    return redirect(url_for('produto.login_vendedor'))

# ------------------- API PARA GERENCIAR PRODUTOS DO VENDEDOR -------------------

@rotas_produto.route('/api/vendedor/produtos', methods=['GET', 'POST'])
def gerenciar_produtos_vendedor():
    """API para gerenciar produtos do vendedor"""
    try:
        if not session.get('vendedor_logado'):
            return jsonify({"erro": "Não autorizado"}), 401

        vendedor_id = session.get('vendedor_id')
        vendedor_nome = session.get('vendedor_nome')

        if request.method == 'POST':
            # Adicionar novo produto
            dados = request.get_json()
            
            nome = dados.get('nome')
            descricao = dados.get('descricao')
            preco = dados.get('preco')
            categoria_id = dados.get('categoria_id')
            estoque = dados.get('estoque', 1)

            if not all([nome, descricao, preco, categoria_id]):
                return jsonify({"erro": "Todos os campos são obrigatórios"}), 400

            conexao = ConexaoBD()
            sql = """
                INSERT INTO produtos_tt 
                (nome, descricao, preco, categoria_id, estoque, criado_por, criado_por_id, criado_em)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """
            conexao.insert(sql, (nome, descricao, preco, categoria_id, estoque, vendedor_nome, vendedor_id))
            conexao.close()

            return jsonify({"mensagem": "Produto adicionado com sucesso!"}), 201

        else:
            # GET - Listar produtos do vendedor
            conexao = ConexaoBD()
            sql = """
                SELECT 
                    p.id_produto,
                    p.nome,
                    p.descricao,
                    p.preco,
                    p.estoque,
                    p.imagem,
                    p.criado_em,
                    c.nome as categoria
                FROM produtos_tt p
                LEFT JOIN categorias_produtos_tt c ON p.categoria_id = c.id_categoria
                WHERE p.criado_por_id = %s
                ORDER BY p.id_produto DESC
            """
            produtos = conexao.select(sql, (vendedor_id,))
            conexao.close()

            produtos_formatados = []
            for produto in produtos:
                produtos_formatados.append({
                    'id': produto[0],
                    'nome': produto[1],
                    'descricao': produto[2],
                    'preco': float(produto[3]),
                    'estoque': produto[4],
                    'imagem': f"/static/tech_trade_imagens/{produto[5]}" if produto[5] else "/static/tech_trade_imagens/default.jpg",
                    'criado_em': produto[6].strftime('%d/%m/%Y') if produto[6] else '',
                    'categoria': produto[7] or 'Sem categoria',
                    'status': 'ativo' if produto[4] > 0 else 'inativo'
                })

            return jsonify({"produtos": produtos_formatados})

    except Exception as e:
        print(f"❌ Erro na API de produtos do vendedor: {e}")
        return jsonify({"erro": str(e)}), 500

# ------------------- ATUALIZAR PRODUTO DO VENDEDOR -------------------

@rotas_produto.route('/api/vendedor/produtos/<int:id_produto>', methods=['PUT', 'DELETE'])
def gerenciar_produto_vendedor(id_produto):
    """Atualizar ou deletar produto do vendedor"""
    try:
        if not session.get('vendedor_logado'):
            return jsonify({"erro": "Não autorizado"}), 401

        vendedor_id = session.get('vendedor_id')
        conexao = ConexaoBD()

        # Verificar se o produto pertence ao vendedor
        sql_verifica = "SELECT id_produto FROM produtos_tt WHERE id_produto = %s AND criado_por_id = %s"
        produto = conexao.select(sql_verifica, (id_produto, vendedor_id))
        
        if not produto:
            conexao.close()
            return jsonify({"erro": "Produto não encontrado ou não pertence ao vendedor"}), 404

        if request.method == 'PUT':
            # Atualizar produto
            dados = request.get_json()
            
            sql = """
                UPDATE produtos_tt 
                SET nome = %s, descricao = %s, preco = %s, categoria_id = %s, 
                    estoque = %s
                WHERE id_produto = %s AND criado_por_id = %s
            """
            conexao.insert(sql, (
                dados.get('nome'),
                dados.get('descricao'),
                dados.get('preco'),
                dados.get('categoria_id'),
                dados.get('estoque'),
                id_produto,
                vendedor_id
            ))
            conexao.close()
            
            return jsonify({"mensagem": "Produto atualizado com sucesso!"})

        else:  # DELETE
            sql = "DELETE FROM produtos_tt WHERE id_produto = %s AND criado_por_id = %s"
            conexao.insert(sql, (id_produto, vendedor_id))
            conexao.close()
            
            return jsonify({"mensagem": "Produto excluído com sucesso!"})

    except Exception as e:
        print(f"❌ Erro ao gerenciar produto: {e}")
        return jsonify({"erro": str(e)}), 500

# ------------------- REGISTRAR COMPRA -------------------

@rotas_produto.route("/techtrade/produtos/finalizar_compra", methods=["POST"])
def finalizar_compra():
    """Registra uma compra no banco de dados"""
    try:
        if not session.get('usuario_logado'):
            return jsonify({"erro": "Usuário não logado"}), 401

        dados = request.get_json()
        
        id_produto = dados.get('id_produto')
        quantidade = dados.get('quantidade', 1)
        metodo_pagamento = dados.get('metodo_pagamento')
        endereco_entrega = dados.get('endereco_entrega', '')
        observacoes = dados.get('observacoes', '')

        if not all([id_produto, metodo_pagamento]):
            return jsonify({"erro": "Dados incompletos"}), 400

        id_cliente = session.get('usuario_id')
        
        conexao = ConexaoBD()

        # Buscar informações do produto
        sql_produto = """
            SELECT preco, criado_por_id, estoque 
            FROM produtos_tt 
            WHERE id_produto = %s
        """
        produto = conexao.select(sql_produto, (id_produto,))
        
        if not produto:
            conexao.close()
            return jsonify({"erro": "Produto não encontrado"}), 404

        preco_unitario = float(produto[0][0])
        id_vendedor = produto[0][1]
        estoque_atual = produto[0][2]
        total = preco_unitario * quantidade

        # Verificar estoque
        if estoque_atual < quantidade:
            conexao.close()
            return jsonify({"erro": "Estoque insuficiente"}), 400

        # Inserir compra
        sql_compra = """
            INSERT INTO compras_tt 
            (id_cliente, id_produto, quantidade, preco_unitario, total, 
             metodo_pagamento, endereco_entrega, observacoes, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pendente')
        """
        conexao.insert(sql_compra, (
            id_cliente, id_produto, quantidade, preco_unitario, total,
            metodo_pagamento, endereco_entrega, observacoes
        ))

        # Atualizar estoque do produto
        sql_estoque = """
            UPDATE produtos_tt 
            SET estoque = estoque - %s 
            WHERE id_produto = %s
        """
        conexao.insert(sql_estoque, (quantidade, id_produto))

        conexao.close()

        print(f"✅ Compra registrada: Cliente {id_cliente} comprou produto {id_produto}")

        return jsonify({
            "mensagem": "Compra realizada com sucesso!",
            "id_compra": "Última inserção"
        }), 201

    except Exception as err:
        print(f"❌ Erro ao registrar compra: {err}")
        return jsonify({"erro": str(err)}), 500

# ------------------- ATUALIZAR STATUS DA COMPRA -------------------

@rotas_produto.route('/api/compras/<int:id_compra>/status', methods=['PUT'])
def atualizar_status_compra(id_compra):
    """Atualiza o status de uma compra"""
    try:
        if not session.get('vendedor_logado'):
            return jsonify({"erro": "Não autorizado"}), 401

        dados = request.get_json()
        novo_status = dados.get('status')
        
        if not novo_status:
            return jsonify({"erro": "Status é obrigatório"}), 400

        conexao = ConexaoBD()
        
        # Verificar se a compra é de um produto deste vendedor
        sql_verifica = """
            SELECT c.id_compra 
            FROM compras_tt c
            INNER JOIN produtos_tt p ON c.id_produto = p.id_produto
            WHERE c.id_compra = %s AND p.criado_por_id = %s
        """
        compra = conexao.select(sql_verifica, (id_compra, session.get('vendedor_id')))
        
        if not compra:
            conexao.close()
            return jsonify({"erro": "Compra não encontrada ou não pertence ao vendedor"}), 404

        # Atualizar status
        sql_update = "UPDATE compras_tt SET status = %s WHERE id_compra = %s"
        conexao.insert(sql_update, (novo_status, id_compra))
        conexao.close()

        return jsonify({"mensagem": f"Status atualizado para '{novo_status}'"}), 200

    except Exception as e:
        print(f"❌ Erro ao atualizar status: {e}")
        return jsonify({"erro": str(e)}), 500

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
        print(f"Erro no comprovante: {e}")
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
            mensagem_notificacao = f"🎉 Nova venda! {nome_produto} vendido para o cliente via {metodo_pagamento}. Total: R$ {total:.2f}"
            
            sql_notificacao = """
                INSERT INTO notificacoes_tt (id_vendedor, mensagem, data_envio, lida)
                VALUES (%s, %s, NOW(), 0)
            """
            conexao.insert(sql_notificacao, (id_vendedor, mensagem_notificacao))
            
            print(f"📩 Notificação criada para vendedor {id_vendedor}: {mensagem_notificacao}")

        conexao.close()

        print(f"✅ Compra registrada: Cliente {id_cliente} comprou produto {id_produto}")
        print(f"📩 Vendedor {nome_vendedor} notificado sobre a venda")

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
        print(f"❌ Erro ao registrar compra completa: {err}")
        import traceback
        traceback.print_exc()
        return jsonify({"erro": str(err)}), 500

@rotas_produto.route("/api/vendedor/notificacoes")
def get_notificacoes_vendedor():
    """API para buscar notificações do vendedor"""
    try:
        if not session.get('vendedor_logado'):
            return jsonify({"erro": "Não autorizado"}), 401

        vendedor_id = session.get('vendedor_id')
        
        conexao = ConexaoBD()
        sql = """
            SELECT id_notificacao, mensagem, data_envio, lida
            FROM notificacoes_tt
            WHERE id_vendedor = %s
            ORDER BY data_envio DESC
            LIMIT 10
        """
        notificacoes = conexao.select(sql, (vendedor_id,))
        conexao.close()

        notificacoes_formatadas = []
        for notif in notificacoes:
            notificacoes_formatadas.append({
                'id': notif[0],
                'mensagem': notif[1],
                'data_envio': notif[2].strftime('%d/%m/%Y %H:%M') if notif[2] else '',
                'lida': bool(notif[3])
            })

        return jsonify({"notificacoes": notificacoes_formatadas})

    except Exception as e:
        print(f"❌ Erro ao buscar notificações: {e}")
        return jsonify({"erro": str(e)}), 500

# ------------------- PÁGINA DE CONFIRMAÇÃO DE COMPRA -------------------

@rotas_produto.route("/confirmacao")
def confirmacao_compra():
    """Página de confirmação de compra"""
    try:
        # Obter parâmetros da URL
        id_produto = request.args.get('produto')
        metodo = request.args.get('metodo', 'PIX')
        nome_produto = request.args.get('nome', 'Produto')
        preco = request.args.get('preco', '0')
        vendedor = request.args.get('vendedor', 'TechTrade')
        
        # Buscar informações completas do produto do banco
        conexao = ConexaoBD()
        sql_produto = """
            SELECT nome, descricao, preco, imagem, criado_por 
            FROM produtos_tt 
            WHERE id_produto = %s
        """
        produto_db = conexao.select(sql_produto, (id_produto,))
        conexao.close()

        if produto_db:
            produto = {
                "id_produto": id_produto,
                "nome": produto_db[0][0],
                "descricao": produto_db[0][1],
                "preco": float(produto_db[0][2]),
                "imagem": f"/static/tech_trade_imagens/{produto_db[0][3]}" if produto_db[0][3] else "/static/tech_trade_imagens/default.jpg",
                "vendedor": produto_db[0][4] or vendedor
            }
        else:
            # Fallback caso não encontre o produto
            produto = {
                "id_produto": id_produto,
                "nome": nome_produto,
                "descricao": f"Descrição do {nome_produto}",
                "preco": float(preco),
                "imagem": "/static/tech_trade_imagens/default.jpg",
                "vendedor": vendedor
            }

        return render_template("confirmacao.html", 
                             produto=produto,
                             metodo=metodo,
                             now=datetime.now(),
                             usuario_nome=session.get('usuario_nome', 'Cliente TechTrade'))

    except Exception as e:
        print(f"❌ Erro na confirmação: {e}")
        # Fallback básico em caso de erro
        produto = {
            "id_produto": request.args.get('produto', '1'),
            "nome": request.args.get('nome', 'Produto'),
            "descricao": "Produto adquirido com sucesso",
            "preco": float(request.args.get('preco', '0')),
            "imagem": "/static/tech_trade_imagens/default.jpg",
            "vendedor": request.args.get('vendedor', 'TechTrade')
        }
        return render_template("confirmacao.html", 
                             produto=produto,
                             metodo=request.args.get('metodo', 'PIX'),
                             now=datetime.now())
    

@rotas_produto.route('/criar_tabela_vendas')
def criar_tabela_vendas():
    try:
        conn = sqlite3.connect('tech_trade.db')
        cursor = conn.cursor()
        
        # Criar tabela de vendas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendedor_id INTEGER NOT NULL,
                cliente_id INTEGER NOT NULL,
                produto_id INTEGER NOT NULL,
                quantidade INTEGER NOT NULL,
                data_venda DATE NOT NULL,
                status TEXT NOT NULL DEFAULT 'pendente',
                FOREIGN KEY (vendedor_id) REFERENCES vendedores(id),
                FOREIGN KEY (cliente_id) REFERENCES clientes(id),
                FOREIGN KEY (produto_id) REFERENCES produtos(id)
            )
        ''')
        
        conn.commit()
        
        # Verificar se a tabela foi criada
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vendas'")
        resultado = cursor.fetchone()
        
        conn.close()
        
        if resultado:
            return "✅ Tabela de vendas criada com sucesso! <a href='/area_vendedor'>Voltar para área do vendedor</a>"
        else:
            return "❌ Erro ao criar tabela de vendas"
    
    except Exception as e:
        return f"Erro ao criar tabela: {e}"

@rotas_produto.route('/criar_tabelas_notificacoes')
def criar_tabelas_notificacoes():
    """Cria as tabelas necessárias para o sistema de notificações"""
    try:
        conexao = ConexaoBD()
        
        # Criar tabela de notificações
        sql_notificacoes = """
            CREATE TABLE IF NOT EXISTS notificacoes_tt (
                id_notificacao INT AUTO_INCREMENT PRIMARY KEY,
                id_vendedor INT NOT NULL,
                mensagem TEXT NOT NULL,
                data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                lida BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (id_vendedor) REFERENCES vendedores_tt(id_vendedor)
            )
        """
        conexao.insert(sql_notificacoes)
        
        # Verificar se a tabela foi criada
        sql_verifica = "SHOW TABLES LIKE 'notificacoes_tt'"
        resultado = conexao.select(sql_verifica)
        
        conexao.close()
        
        if resultado:
            return "✅ Tabela de notificações criada/verificada com sucesso! <a href='/vendedor/compras'>Voltar para compras</a>"
        else:
            return "❌ Erro ao criar tabela de notificações"
    
    except Exception as e:
        return f"Erro ao criar tabelas: {e}"
# ------------------- PÁGINA DE SUPORTE DO COMPRADOR -------------------

@rotas_produto.route('/suporte_comprador')
def suporte_comprador():
    """Página de suporte e ajuda para compradores"""
    return render_template('suporte_comprador.html')