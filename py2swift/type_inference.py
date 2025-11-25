import ast
from typing import Dict, Optional, Set, List, Any

class TypeInferencer(ast.NodeVisitor):
    """Realiza inferência de tipos em múltiplos passes"""
    
    def __init__(self):
        self.func_signatures: Dict[str, Dict[str, str]] = {}  # func -> {param: type, 'return': type}
        self.var_types: Dict[str, str] = {}  # var -> type
        self.function_return_types: Dict[str, str] = {}  # func -> return_type
        
    def infer(self, tree: ast.AST):
        """Executa inferência em múltiplos passes"""
        # Pass 1: Coleta assinaturas de funções
        self._collect_function_signatures(tree)
        # Pass 2: Infere tipos de variáveis e retornos
        self._infer_types(tree)
    
    def _collect_function_signatures(self, tree: ast.AST):
        """Coleta informações básicas das funções"""
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
                
                self.func_signatures[node.name] = sig
    
    def _infer_types(self, tree: ast.AST):
        """Infere tipos de variáveis e retornos de função"""
        # Primeiro, infere tipos básicos
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                self._infer_assignment(node)
            elif isinstance(node, ast.FunctionDef):
                self._infer_function_types(node)
    
    def _infer_assignment(self, node: ast.Assign):
        """Infere tipos de variáveis através de atribuições"""
        typ = self._infer_expr_type(node.value)
        if typ:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.var_types[target.id] = typ
    
    def _infer_function_types(self, node: ast.FunctionDef):
        """Infere tipos de retorno e parâmetros de função"""
        return_type = self._infer_return_type(node)
        
        # Atualiza assinatura da função
        if node.name in self.func_signatures:
            self.func_signatures[node.name]['return'] = return_type
            
            # Infere tipos de parâmetros baseados no uso
            for arg in node.args.args:
                if arg.arg == 'self':
                    continue
                if arg.arg not in self.func_signatures[node.name] or self.func_signatures[node.name][arg.arg] == 'Any':
                    param_type = self._infer_parameter_type(node, arg.arg)
                    if param_type:
                        self.func_signatures[node.name][arg.arg] = param_type
    
    def _infer_parameter_type(self, func: ast.FunctionDef, param_name: str) -> Optional[str]:
        """Infere tipo de parâmetro baseado no uso dentro da função"""
        param_types = set()
        
        for node in ast.walk(func):
            # Procura por usos do parâmetro em operações
            if isinstance(node, ast.Name) and node.id == param_name:
                # Verifica o contexto do uso
                parent = self._get_parent_context(func, node)
                if parent:
                    if isinstance(parent, ast.BinOp):
                        # Operações matemáticas sugerem Int ou Double
                        if isinstance(parent.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
                            left_type = self._infer_expr_type(parent.left) if hasattr(parent, 'left') else None
                            right_type = self._infer_expr_type(parent.right) if hasattr(parent, 'right') else None
                            
                            if left_type == 'Double' or right_type == 'Double':
                                param_types.add('Double')
                            else:
                                param_types.add('Int')
                    
                    elif isinstance(parent, ast.Compare):
                        # Comparações com números
                        for comparator in parent.comparators:
                            comp_type = self._infer_expr_type(comparator)
                            if comp_type in ('Int', 'Double'):
                                param_types.add(comp_type)
        
        if param_types:
            # Prefere tipos mais específicos
            if 'Int' in param_types and 'Double' not in param_types:
                return 'Int'
            elif 'Double' in param_types:
                return 'Double'
            return param_types.pop()
        
        return None
    
    def _get_parent_context(self, tree: ast.AST, target: ast.AST) -> Optional[ast.AST]:
        """Encontra o contexto pai de um nó"""
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                if child is target:
                    return parent
        return None
    
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
        
        # Para múltiplos tipos de retorno, tenta encontrar um tipo comum
        if return_types == {'Int', 'Double'}:
            return 'Double'  # Promove para Double se misturar Int e Double
        
        # CORREÇÃO: Se todos os retornos são inteiros ou operações com inteiros, retorna Int
        if self._all_returns_are_int(func):
            return 'Int'
        
        return 'Any'
    
    def _all_returns_are_int(self, func: ast.FunctionDef) -> bool:
        """Verifica se todos os retornos da função são inteiros"""
        for node in ast.walk(func):
            if isinstance(node, ast.Return) and node.value:
                if not self._is_int_expression(node.value):
                    return False
        return True
    
    def _is_int_expression(self, node: ast.AST) -> bool:
        """Verifica se uma expressão resulta em Int"""
        expr_type = self._infer_expr_type(node)
        if expr_type == 'Int':
            return True
        
        # Verificação mais detalhada para expressões complexas
        if isinstance(node, ast.Constant):
            return isinstance(node.value, int)
        
        elif isinstance(node, ast.BinOp):
            if isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod)):
                return (self._is_int_expression(node.left) and 
                        self._is_int_expression(node.right))
        
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                # Para chamadas recursivas, verifica se a função retorna Int
                func_name = node.func.id
                if func_name in self.func_signatures:
                    return self.func_signatures[func_name].get('return') == 'Int'
            return False
        
        elif isinstance(node, ast.Name):
            # Verifica se a variável é Int
            if node.id in self.var_types:
                return self.var_types[node.id] == 'Int'
            # Verifica se é parâmetro da função
            for func_sig in self.func_signatures.values():
                if node.id in func_sig:
                    return func_sig[node.id] == 'Int'
            return False
        
        return False
    
    def _infer_expr_type(self, node: ast.AST) -> Optional[str]:
        """Infere tipo de uma expressão com mais precisão"""
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
            if v is None:
                return 'Void'
        
        elif isinstance(node, ast.List):
            if node.elts:
                # Tenta inferir tipo baseado nos elementos
                elem_types = set()
                for elem in node.elts:
                    elem_type = self._infer_expr_type(elem)
                    if elem_type:
                        elem_types.add(elem_type)
                
                if len(elem_types) == 1:
                    return f'[{elem_types.pop()}]'
            return '[Any]'
        
        elif isinstance(node, ast.Dict):
            if node.keys and node.values:
                key_types = set()
                val_types = set()
                
                for key in node.keys:
                    key_type = self._infer_expr_type(key)
                    if key_type:
                        key_types.add(key_type)
                
                for val in node.values:
                    val_type = self._infer_expr_type(val)
                    if val_type:
                        val_types.add(val_type)
                
                if len(key_types) == 1 and len(val_types) == 1:
                    return f'[{key_types.pop()}: {val_types.pop()}]'
            return '[String: Any]'
        
        elif isinstance(node, ast.BinOp):
            left_type = self._infer_expr_type(node.left)
            right_type = self._infer_expr_type(node.right)
            
            # CORREÇÃO: Para operações matemáticas com inteiros, mantém como Int
            if left_type == 'Int' and right_type == 'Int':
                if isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Mod)):
                    return 'Int'
                elif isinstance(node.op, ast.Div):
                    # Divisão de inteiros pode resultar em Double
                    return 'Double'
            
            if left_type and right_type:
                # Operações matemáticas
                if isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod)):
                    if left_type == 'Double' or right_type == 'Double':
                        return 'Double'
                    elif left_type == 'Int' and right_type == 'Int':
                        return 'Int'  # Já tratado acima, mas mantido para clareza
                    elif left_type == 'String' or right_type == 'String':
                        return 'String'
                
                # Operações de comparação sempre retornam Bool
                elif isinstance(node.op, (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
                    return 'Bool'
            
            return left_type or right_type
        
        elif isinstance(node, ast.UnaryOp):
            operand_type = self._infer_expr_type(node.operand)
            if isinstance(node.op, ast.Not) and operand_type == 'Bool':
                return 'Bool'
            return operand_type
        
        elif isinstance(node, ast.BoolOp):
            # Operações lógicas sempre retornam Bool
            return 'Bool'
        
        elif isinstance(node, ast.Compare):
            # Comparações sempre retornam Bool
            return 'Bool'
        
        elif isinstance(node, ast.Name):
            # Verifica se é uma variável conhecida
            if node.id in self.var_types:
                return self.var_types[node.id]
            
            # Verifica se é um parâmetro de função
            for func_sig in self.func_signatures.values():
                if node.id in func_sig and func_sig[node.id] != 'Any':
                    return func_sig[node.id]
            
            # Constantes built-in
            if node.id in ('True', 'False'):
                return 'Bool'
            if node.id == 'None':
                return 'Void'
        
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                
                # Verifica assinatura conhecida
                if func_name in self.func_signatures:
                    return self.func_signatures[func_name].get('return', 'Any')
                
                # Mapeamento de built-ins comuns
                builtin_returns = {
                    'int': 'Int',
                    'float': 'Double', 
                    'str': 'String',
                    'bool': 'Bool',
                    'len': 'Int',
                    'sum': 'Int',
                    'min': 'Any',
                    'max': 'Any',
                    'abs': 'Any',
                    'print': 'Void',
                    'range': 'Range',
                    'list': '[Any]',
                    'dict': '[String: Any]',
                }
                return builtin_returns.get(func_name, 'Any')
            
            elif isinstance(node.func, ast.Attribute):
                # Para métodos, retorna Any por padrão
                return 'Any'
        
        elif isinstance(node, ast.Subscript):
            container_type = self._infer_expr_type(node.value)
            if container_type and container_type.startswith('['):
                # Para arrays, retorna o tipo do elemento
                if container_type.endswith(']'):
                    return container_type[1:-1]  # Extrai o tipo interno
            return 'Any'
        
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
                'None': 'Void',
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