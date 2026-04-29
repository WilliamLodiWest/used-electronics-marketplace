# criar_vendedora.py - Execute este script APENAS UMA VEZ para criar sua conta de vendedora
from werkzeug.security import generate_password_hash
from src.utils.bd import ConexaoBD

def criar_vendedora():
    """Cria a conta da vendedora/dona da loja"""
    
    # Seus dados de acesso
    nome = "Seu Nome"  # Coloque seu nome
    email = "seu@email.com"  # Coloque seu email
    senha = "suasenha123"  # Coloque uma senha forte
    telefone = "(11) 99999-9999"  # Seu telefone
    documento = "000.000.000-00"  # Seu CPF
    loja_nome = "TechTrade Official"  # Nome da sua loja
    loja_descricao = "Loja oficial da TechTrade"
    
    try:
        conexao = ConexaoBD()
        
        # Verificar se já existe
        existe = conexao.select("SELECT id_vendedor FROM vendedores_tt WHERE email = %s", (email,))
        if existe:
            print(f"⚠️ Já existe uma vendedora cadastrada com o email {email}")
            print("Se quiser recriar, primeiro delete do banco de dados")
            conexao.close()
            return
        
        hash_senha = generate_password_hash(senha, method='pbkdf2:sha256')
        
        sql = """
            INSERT INTO vendedores_tt (nome, email, senha, telefone, documento, loja_nome, loja_descricao, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'ativo')
        """
        conexao.insert(sql, (nome, email, hash_senha, telefone, documento, loja_nome, loja_descricao))
        conexao.close()
        
        print("✅ Vendedora cadastrada com sucesso!")
        print(f"📧 Email: {email}")
        print(f"🔑 Senha: {senha}")
        print("\n⚠️ Guarde essas informações em segurança!")
        
    except Exception as e:
        print(f"❌ Erro ao cadastrar: {e}")

if __name__ == "__main__":
    criar_vendedora()