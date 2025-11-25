import ast
from typing import List
from .exceptions import UnsupportedFeatureError

class LexicalAnalyzer:
    """Analisador léxico - identifica tokens e estruturas básicas"""
    
    def __init__(self):
        self.warnings: List[str] = []
    
    def analyze(self, source: str) -> ast.AST:
        """Realiza análise léxica e sintática"""
        try:
            return ast.parse(source)
        except SyntaxError as e:
            raise UnsupportedFeatureError(f"Erro de sintaxe Python: {e}", None)
    
    def escape_string(self, s: str) -> str:
        """Escapa string corretamente para Swift"""
        return (s.replace('\\', '\\\\')
                 .replace('"', '\\"')
                 .replace('\n', '\\n')
                 .replace('\t', '\\t')
                 .replace('\r', '\\r'))
    
    def warn(self, message: str, node: ast.AST = None):
        """Adiciona um aviso"""
        if node and hasattr(node, 'lineno'):
            message = f"Linha {node.lineno}: {message}"
        self.warnings.append(message)