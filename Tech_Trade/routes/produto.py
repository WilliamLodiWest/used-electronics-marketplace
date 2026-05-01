from datetime import datetime, timedelta
from src.utils.bd import ConexaoBD
from flask import Blueprint, flash, jsonify, render_template, request, abort, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import hashlib
import os
import secrets

BASE_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PERFIS_CLIENTES_DIR = os.path.join(BASE_APP_DIR, 'static', 'perfis_clientes')
_FOTO_EXTS = ('.webp', '.png', '.jpg', '.jpeg')


def _dir_perfis_clientes():
    os.makedirs(_PERFIS_CLIENTES_DIR, exist_ok=True)
    return _PERFIS_CLIENTES_DIR


def _foto_url_cliente(id_cliente):
    d = _dir_perfis_clientes()
    for ext in _FOTO_EXTS:
        p = os.path.join(d, f'{id_cliente}{ext}')
        if os.path.isfile(p):
            return f'/static/perfis_clientes/{id_cliente}{ext}'
    return ''


def _iniciais_nome(nome):
    nome = (nome or '').strip()
    if not nome:
        return ''
    partes = [p for p in nome.split() if p]
    if len(partes) >= 2:
        return (partes[0][0] + partes[-1][0]).upper()
    return nome[:2].upper()


def _apagar_fotos_cliente(id_cliente):
    d = _dir_perfis_clientes()
    for ext in _FOTO_EXTS:
        p = os.path.join(d, f'{id_cliente}{ext}')
        try:
            if os.path.isfile(p):
                os.remove(p)
        except OSError:
            pass


def _salvar_foto_perfil(id_cliente, file_storage):
    """Salva arquivo de imagem; retorna mensagem de erro ou None."""
    if not file_storage or not file_storage.filename:
        return None
    ctype = (file_storage.content_type or '').lower()
    ext_por_tipo = {
        'image/jpeg': '.jpg',
        'image/jpg': '.jpg',
        'image/png': '.png',
        'image/webp': '.webp',
    }
    ext = ext_por_tipo.get(ctype)
    if not ext:
        return 'Envie uma imagem JPG, PNG ou WebP.'
    file_storage.seek(0, os.SEEK_END)
    tamanho = file_storage.tell()
    file_storage.seek(0)
    if tamanho > 5 * 1024 * 1024:
        return 'Arquivo muito grande. Máximo 5 MB.'
    _apagar_fotos_cliente(id_cliente)
    destino = os.path.join(_dir_perfis_clientes(), f'{id_cliente}{ext}')
    file_storage.save(destino)
    return None

rotas_produto = Blueprint('produto', __name__)

# ------------------- RENDERIZAÇÃO DE PÁGINAS -------------------

@rotas_produto.route('/')
def home():
    """Página inicial"""
    usuario_foto_url = None
    usuario_iniciais = ''
    if session.get('usuario_logado') and session.get('usuario_id'):
        try:
            uid = int(session['usuario_id'])
            usuario_foto_url = _foto_url_cliente(uid) or None
        except (TypeError, ValueError):
            usuario_foto_url = None
        usuario_iniciais = _iniciais_nome(session.get('usuario_nome'))
    return render_template(
        'home.html',
        usuario_foto_url=usuario_foto_url,
        usuario_iniciais=usuario_iniciais,
    )

# ------------------- LOGIN DE CLIENTE -------------------

@rotas_produto.route('/login', methods=['GET', 'POST'])
def login():
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
            flash("E-mail ou senha incorretos.", "erro")
            return redirect(url_for('produto.login'))

    return render_template('login.html')

@rotas_produto.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('produto.home'))


@rotas_produto.route('/perfil/editar', methods=['GET', 'POST'])
def editar_perfil():
    """Tela e envio do formulário de perfil do comprador (sessão)."""
    if not session.get('usuario_logado') or not session.get('usuario_id'):
        flash('Faça login para acessar seu perfil.', 'erro')
        return redirect(url_for('produto.login'))

    id_cliente = int(session['usuario_id'])
    sucesso = None
    erro = None

    def carregar_dados_formulario(msg_erro=None):
        conexao = ConexaoBD()
        rows = conexao.select(
            'SELECT nome, email, telefone FROM clientes_tt WHERE id_cliente = %s',
            (id_cliente,),
        )
        conexao.close()
        if not rows:
            session.clear()
            flash('Sessão inválida. Faça login novamente.', 'erro')
            return redirect(url_for('produto.login'))
        nome_db, email_db, tel_db = rows[0][0], rows[0][1], rows[0][2]
        foto = _foto_url_cliente(id_cliente)
        return render_template(
            'editar_perfil.html',
            nome=nome_db,
            email=email_db,
            telefone=tel_db or '',
            foto_url=foto,
            sucesso=sucesso,
            erro=msg_erro or erro,
        )

    if request.method == 'POST':
        nome = (request.form.get('nome') or '').strip()
        email = (request.form.get('email') or '').strip()
        telefone = (request.form.get('telefone') or '').strip()
        senha_atual = request.form.get('senha_atual') or ''
        nova_senha = request.form.get('nova_senha') or ''
        confirmar_senha = request.form.get('confirmar_senha') or ''
        remover_foto = request.form.get('remover_foto') == '1'

        if not nome or not email or not telefone:
            return carregar_dados_formulario('Preencha nome, e-mail e telefone.')

        conexao = ConexaoBD()
        duplicado = conexao.select(
            'SELECT id_cliente FROM clientes_tt WHERE email = %s AND id_cliente <> %s',
            (email, id_cliente),
        )
        if duplicado:
            conexao.close()
            return carregar_dados_formulario('Este e-mail já está em uso por outra conta.')

        row_senha = conexao.select(
            'SELECT senha FROM clientes_tt WHERE id_cliente = %s',
            (id_cliente,),
        )
        if not row_senha:
            conexao.close()
            session.clear()
            return redirect(url_for('produto.login'))

        hash_atual = row_senha[0][0]
        campos_senha = [bool(senha_atual.strip()), bool(nova_senha.strip()), bool(confirmar_senha.strip())]
        if any(campos_senha) and not all(campos_senha):
            conexao.close()
            return carregar_dados_formulario(
                'Para alterar a senha, preencha senha atual, nova senha e confirmação.'
            )

        if nova_senha.strip():
            if len(nova_senha) < 6:
                conexao.close()
                return carregar_dados_formulario('A nova senha deve ter no mínimo 6 caracteres.')
            if nova_senha != confirmar_senha:
                conexao.close()
                return carregar_dados_formulario('A nova senha e a confirmação não conferem.')
            if not check_password_hash(hash_atual, senha_atual):
                conexao.close()
                return carregar_dados_formulario('Senha atual incorreta.')
            novo_hash = generate_password_hash(nova_senha, method='pbkdf2:sha256')
            conexao.update(
                'UPDATE clientes_tt SET nome=%s, email=%s, telefone=%s, senha=%s WHERE id_cliente=%s',
                (nome, email, telefone, novo_hash, id_cliente),
            )
        else:
            conexao.update(
                'UPDATE clientes_tt SET nome=%s, email=%s, telefone=%s WHERE id_cliente=%s',
                (nome, email, telefone, id_cliente),
            )

        conexao.close()

        if remover_foto:
            _apagar_fotos_cliente(id_cliente)

        arquivo = request.files.get('foto_perfil')
        if arquivo and arquivo.filename:
            err_foto = _salvar_foto_perfil(id_cliente, arquivo)
            if err_foto:
                return carregar_dados_formulario(err_foto)

        session['usuario_nome'] = nome
        sucesso_local = 'Perfil atualizado com sucesso.'
        foto_url = _foto_url_cliente(id_cliente)
        return render_template(
            'editar_perfil.html',
            nome=nome,
            email=email,
            telefone=telefone,
            foto_url=foto_url,
            sucesso=sucesso_local,
            erro=None,
        )

    return carregar_dados_formulario()

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
                return render_template('login.html', erro="Preencha todos os campos obrigatórios.")

            conexao = ConexaoBD()

            # Verifica se já existe
            sql_verifica = "SELECT id_cliente FROM clientes_tt WHERE email = %s"
            existente = conexao.select(sql_verifica, (email,))
            if existente:
                conexao.close()
                return render_template('login.html', erro="E-mail já cadastrado.")

            # Inserir cliente
            hash_senha = generate_password_hash(senha, method='pbkdf2:sha256')
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

        return render_template('login.html')

    except Exception as err:
        return render_template('login.html', erro="Erro ao cadastrar.")

# ------------------- RECUPERAÇÃO DE SENHA -------------------

@rotas_produto.route('/esqueceu_senha', methods=['GET', 'POST'])
def esqueceu_senha():
    """Página e API para solicitar recuperação de senha"""
    try:
        if request.method == 'POST':
            email = request.form.get('email')
            
            if not email:
                return jsonify({"erro": "Por favor, informe seu e-mail."}), 400
            
            conexao = ConexaoBD()
            
            sql = "SELECT id_cliente, nome FROM clientes_tt WHERE email = %s"
            usuario = conexao.select(sql, (email,))
            
            if usuario:
                token = secrets.token_urlsafe(32)
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                expiracao = datetime.now() + timedelta(hours=1)
                
                sql_token = """
                    INSERT INTO recuperacao_senha_tt (id_cliente, token, expiracao, usado)
                    VALUES (%s, %s, %s, 0)
                """
                conexao.insert(sql_token, (usuario[0][0], token_hash, expiracao))
                
                link_recuperacao = url_for('produto.redefinir_senha', token=token, _external=True)
                
                conexao.close()
                
                return jsonify({
                    "success": True,
                    "message": "Link de recuperação gerado!",
                    "link": link_recuperacao
                }), 200
            else:
                conexao.close()
                return jsonify({
                    "success": True,
                    "message": "Se o e-mail estiver cadastrado, você receberá as instruções."
                }), 200
        
        return render_template('login.html')
    
    except Exception as err:
        return jsonify({"erro": str(err)}), 500

@rotas_produto.route('/redefinir_senha/<token>', methods=['GET', 'POST'])
def redefinir_senha(token):
    """Página para redefinir a senha usando o token"""
    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        conexao = ConexaoBD()
        
        sql = """
            SELECT r.id_cliente, c.nome, r.expiracao
            FROM recuperacao_senha_tt r
            JOIN clientes_tt c ON r.id_cliente = c.id_cliente
            WHERE r.token = %s AND r.usado = 0
        """
        recuperacao = conexao.select(sql, (token_hash,))
        
        if not recuperacao:
            conexao.close()
            return render_template('login.html', 
                                 erro_token="Token inválido ou já utilizado.")
        
        id_cliente = recuperacao[0][0]
        nome_cliente = recuperacao[0][1]
        expiracao = recuperacao[0][2]
        
        if datetime.now() > expiracao:
            conexao.close()
            return render_template('login.html', 
                                 erro_token="Token expirado. Solicite uma nova recuperação.")
        
        if request.method == 'POST':
            nova_senha = request.form.get('nova_senha')
            confirmar_senha = request.form.get('confirmar_senha')
            
            if not nova_senha or not confirmar_senha:
                return render_template('login.html', 
                                    erro="Preencha todos os campos.",
                                    token=token,
                                    show_reset=True)

            if nova_senha != confirmar_senha:
                return render_template('login.html', 
                                    erro="As senhas não conferem.",
                                    token=token,
                                    show_reset=True)

            if len(nova_senha) < 6:
                return render_template('login.html', 
                                    erro="A senha deve ter no mínimo 6 caracteres.",
                                    token=token,
                                    show_reset=True)

            hash_senha = generate_password_hash(nova_senha, method='pbkdf2:sha256')
            sql_update = "UPDATE clientes_tt SET senha = %s WHERE id_cliente = %s"
            conexao.update(sql_update, (hash_senha, id_cliente))

            sql_token = "UPDATE recuperacao_senha_tt SET usado = 1 WHERE token = %s"
            conexao.update(sql_token, (token_hash,))

            conexao.close()

            flash("Senha redefinida com sucesso! Faça login.", "sucesso")
            return redirect(url_for('produto.login'))
        
        conexao.close()
        
        return render_template('login.html', 
                             token=token,
                             nome_cliente=nome_cliente,
                             show_reset=True)
    
    except Exception as err:
        return render_template('login.html', erro="Erro ao processar solicitação.")

# Importa os módulos divididos para registrar rotas no mesmo blueprint.
try:
    from . import administrador  # noqa: F401
    from . import produtos_suporte  # noqa: F401
    from . import suporte_chat_ia  # noqa: F401
    from . import vendedor  # noqa: F401
except ImportError:
    import administrador  # noqa: F401
    import produtos_suporte  # noqa: F401
    import suporte_chat_ia  # noqa: F401
    import vendedor  # noqa: F401