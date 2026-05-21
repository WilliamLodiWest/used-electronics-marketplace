from flask import jsonify, request, session
from src.utils.bd import ConexaoBD
from src.utils.schema_compat import table_has_column

try:
    from .produto import rotas_produto
except ImportError:
    from produto import rotas_produto


@rotas_produto.route('/techtrade/produtos/verificar', methods=['POST'])
def verificar_produto():
    """Marca um produto como verificado."""
    try:
        if not session.get('is_admin'):
            return jsonify({"erro": "Acesso restrito à administradora."}), 403

        dados = request.get_json() or {}
        id_produto = dados.get('id_produto')
        verificado = dados.get('verificado', True)
        verificado = dados.get('verificado', 'Sistema')
        verificacao_obs = dados.get('verificacao_obs', '')
        chave_raw = dados.get('chave_nfe') or ''
        chave_nfe = ''.join(c for c in str(chave_raw) if c.isdigit())

        if not id_produto:
            return jsonify({"erro": "ID do produto é obrigatório"}), 400

        if chave_nfe and len(chave_nfe) != 44:
            return jsonify({"erro": "Chave de acesso da NF-e deve ter exatamente 44 dígitos."}), 400

        conexao = ConexaoBD()
        if table_has_column(conexao, "produtos_tt", "chave_nfe"):
            sql = """
                UPDATE produtos_tt
                SET verificado = %s,
                    verificado = %s,
                    verificado_em = NOW(),
                    verificacao_obs = %s,
                    chave_nfe = %s
                WHERE id_produto = %s
            """
            chave_val = chave_nfe if chave_nfe else None
            conexao.insert(sql, (1 if verificado else 0, verificado, verificacao_obs, chave_val, id_produto))
        else:
            sql = """
                UPDATE produtos_tt
                SET verificado = %s,
                    verificado = %s,
                    verificado_em = NOW(),
                    verificacao_obs = %s
                WHERE id_produto = %s
            """
            conexao.insert(sql, (1 if verificado else 0, verificado, verificacao_obs, id_produto))
        conexao.close()

        return jsonify({"mensagem": "Produto verificado com sucesso!"}), 200
    except Exception as err:
        return jsonify({"erro": str(err)}), 500