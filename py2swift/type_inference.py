import ast
from typing import Dict, Optional, Set

class TypeInferencer(ast.NodeVisitor):
    """Realiza inferência de tipos em múltiplos passes"""
    
    def __init__(self):
        self.func_signatures: Dict[str, Dict[str, str]] = {}  # func -> {param: type, 'return': type}
        self.var_types: Dict[str, str] = {}  # var -> type
        
    def infer(self, tree: ast.AST):
        """Executa inferência em múltiplos passes"""
        # Pass 1: Coleta assinaturas de funções
        self._collect_function_signatures(tree)
        # Pass 2: Infere tipos de variáveis
        self._infer_variable_types(tree)
    
    def _collect_function_signatures(self, tree: ast.AST):
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                sig = {'return': 'Void'}
                
                # Coleta tipos de argumentos
                for arg in node.args.args:
                    if arg.arg == 'self':
                        continue
                    # Usa annotation se disponível
                    if arg.annotation:
                        sig[arg.arg] = self._annotation_to_swift(arg.annotation)
                    else:
                        sig[arg.arg] = 'Any'
                
                # Tenta inferir tipo de retorno
                if node.returns:
                    sig['return'] = self._annotation_to_swift(node.returns)
                else:
                    sig['return'] = self._infer_return_type(node)
                
                self.func_signatures[node.name] = sig
    
    def _infer_return_type(self, func: ast.FunctionDef) -> str:
        """Infere tipo de retorno analisando statements return"""
        return_types = set()
        
        for node in ast.walk(func):
            if isinstance(node, ast.Return) and node.value:
                rt = self._infer_expr_type(node.value)
                if rt:
                    return_types.add(rt)
        
        if not return_types:
            return 'Void'
        if len(return_types) == 1:
            return return_types.pop()
        # Múltiplos tipos -> usa Any
        return 'Any'
    
    def _infer_variable_types(self, tree: ast.AST):
        """Infere tipos de variáveis através de atribuições"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                typ = self._infer_expr_type(node.value)
                if typ:
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            self.var_types[target.id] = typ
    
    def _infer_expr_type(self, node: ast.AST) -> Optional[str]:
        """Infere tipo de uma expressão"""
        if isinstance(node, ast.Constant):
            v = node.value
            if isinstance(v, bool):
                return 'Bool'
            if isinstance(v, int):
                return 'Int'
            if isinstance(v, float):
                return 'Double'
            if isinstance(v, str):
                return 'String'
        
        elif isinstance(node, ast.List):
            if node.elts:
                # Simplificação: usa o tipo do primeiro elemento.
                elem_type = self._infer_expr_type(node.elts[0])
                return f'[{elem_type}]' if elem_type else '[Any]'
            return '[Any]'
        
        elif isinstance(node, ast.Dict):
            if node.keys and node.values:
                # Simplificação: usa o tipo do primeiro par.
                key_type = self._infer_expr_type(node.keys[0])
                val_type = self._infer_expr_type(node.values[0])
                if key_type and val_type:
                    return f'[{key_type}: {val_type}]'
            return '[String: Any]'
        
        elif isinstance(node, ast.BinOp):
            left = self._infer_expr_type(node.left)
            right = self._infer_expr_type(node.right)
            if left == right:
                return left
            if left in ('Double', 'Int') and right in ('Double', 'Int'):
                return 'Double' # Promote to Double if mixed numeric
        
        elif isinstance(node, ast.Name):
            return self.var_types.get(node.id)
        
        # Chamadas de função: Tenta inferir pelo nome da função
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in self.func_signatures:
                return self.func_signatures[func_name].get('return')
            
            # Mapeamento de builtins comuns
            if func_name in ('int', 'len', 'sum', 'min', 'max'):
                return 'Int'
            if func_name in ('float', 'abs'):
                return 'Double'
            if func_name == 'str':
                return 'String'
            if func_name == 'list':
                return '[Any]'
        
        return None
    
    def _annotation_to_swift(self, node: ast.AST) -> str:
        """Converte annotation Python para tipo Swift"""
        if isinstance(node, ast.Name):
            mapping = {
                'int': 'Int',
                'float': 'Double',
                'str': 'String',
                'bool': 'Bool',
                'list': '[Any]',
                'dict': '[String: Any]',
            }
            return mapping.get(node.id, node.id)
        
        elif isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name):
                if node.value.id == 'List':
                    elem = self._annotation_to_swift(node.slice)
                    return f'[{elem}]'
                elif node.value.id == 'Dict':
                    if isinstance(node.slice, ast.Tuple) and len(node.slice.elts) == 2:
                        k = self._annotation_to_swift(node.slice.elts[0])
                        v = self._annotation_to_swift(node.slice.elts[1])
                        return f'[{k}: {v}]'
        
        return 'Any'