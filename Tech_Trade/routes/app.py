import os

from flask import Flask
from produto import rotas_produto  # Importe do arquivo produto.py no mesmo diretório

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = (
    os.environ.get('SECRET_KEY')
    or os.environ.get('FLASK_SECRET_KEY')
    or 'dev-only-change-in-production'
)

app.register_blueprint(rotas_produto)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=port, debug=debug)