from flask import Flask, render_template, request, jsonify
import os
import sys
import logging

# Garante que o transpiler.py seja encontrado
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from py2swift import transpile, TranspileError

# Configuração básica de logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__, template_folder="templates")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/transpile', methods=['POST'])
def transpile_code():
    data = request.json or {}
    src = data.get('source', '')
    logging.debug(f"Código recebido para transpilar: {src}")

    try:
        output = transpile(src)
        logging.debug("Transpiração bem-sucedida.")
        return jsonify({
            'success': True,
            'output': output
        })

    except TranspileError as e:
        logging.error(f"Erro de transpile: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"Erro de Transpiler: {str(e)}. Verifique o código Python fornecido e tente novamente."
        }), 400

    except Exception as e:
        logging.exception("Erro inesperado durante a transpiração.")
        return jsonify({
            'success': False,
            'error': f"Erro Interno do Servidor: {str(e)}. Por favor, entre em contato com o suporte."
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'Python to Swift Transpiler API'
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)