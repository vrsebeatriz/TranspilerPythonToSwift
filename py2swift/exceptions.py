# ===== EXCEÇÕES PERSONALIZADAS =====
class TranspileError(Exception):
    """Erro base para transpilação"""
    pass

class UnsupportedFeatureError(TranspileError):
    """Recurso do Python não suportado"""
    def __init__(self, feature: str, node):
        self.feature = feature
        self.line = getattr(node, 'lineno', None)
        msg = f"Recurso não suportado: {feature}"
        if self.line:
            msg += f" (linha {self.line})"
        super().__init__(msg)