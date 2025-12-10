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
            tree = ast.parse(source)
            self.detect_unsupported_features(tree)
            return tree
        except SyntaxError as e:
            raise UnsupportedFeatureError(f"Erro de sintaxe Python: {e}", None)
    
    def tokenize(self, source: str) -> List[str]:
        """Identifica e classifica tokens no código-fonte."""
        import tokenize
        from io import StringIO

        tokens = []
        try:
            for tok in tokenize.generate_tokens(StringIO(source).readline):
                tokens.append((tok.type, tok.string))
        except tokenize.TokenError as e:
            self.warn(f"Erro ao tokenizar: {e}")
        return tokens

    def detect_unsupported_features(self, tree: ast.AST):
        """Detecta estruturas Python não suportadas."""
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                self.warn("Funções assíncronas não são suportadas.", node)
            elif isinstance(node, ast.Yield):
                self.warn("Expressões 'yield' não são suportadas.", node)

    def escape_string(self, s: str) -> str:
        """Escapa string corretamente para Swift, incluindo Unicode."""
        return (s.replace('\\', '\\\\')
                 .replace('"', '\\"')
                 .replace('\n', '\\n')
                 .replace('\t', '\\t')
                 .replace('\r', '\\r')
                 .encode('unicode_escape').decode('utf-8'))

    def warn(self, message: str, node: ast.AST = None):
        """Adiciona um aviso"""
        if node and hasattr(node, 'lineno'):
            message = f"Linha {node.lineno}: {message}"
        self.warnings.append(message)
    
    def report_warnings(self):
        """Exibe os avisos armazenados de forma organizada."""
        if not self.warnings:
            print("Nenhum aviso encontrado.")
        else:
            print("Avisos detectados:")
            for warning in self.warnings:
                print(f"- {warning}")