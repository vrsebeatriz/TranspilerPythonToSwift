from flask import Flask, render_template, request, jsonify
import os
import sys

# Garante que o transpiler.py seja encontrado
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from py2swift.transpiler import transpile, TranspileError

app = Flask(__name__, template_folder="templates")

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/transpile', methods=['POST'])
def transpile_code():
    data = request.json or {}
    src = data.get('source', '')
    
    try:
        output = transpile(src)
        return jsonify({
            'success': True,
            'output': output
        })
    
    except TranspileError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Erro inesperado: {str(e)}"
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'Python to Swift Transpiler API'
    })


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
