import ast
from typing import List, Optional, Dict, Any, Set, Tuple

from .exceptions import TranspileError, UnsupportedFeatureError
from .symbol_table import SymbolTable, Symbol
from .type_inference import TypeInferencer
from .lexer import LexicalAnalyzer

class PyToSwiftTranspiler(ast.NodeVisitor):
    def __init__(self):
        self.lines: List[str] = []
        self.indent_level: int = 0
        self.current_class: Optional[str] = None
        self.symbol_table = SymbolTable()
        self.type_inferencer = TypeInferencer()
        self.lexer = LexicalAnalyzer()
    
    # ===== UTILITÁRIOS =====
    def indent(self) -> str:
        return "    " * self.indent_level
    
    def emit(self, line: str = ""):
        self.lines.append(f"{self.indent()}{line}")
    
    def warn(self, message: str, node: ast.AST = None):
        self.lexer.warn(message, node)
    
    @property
    def warnings(self):
        return self.lexer.warnings
    
    def escape_string(self, s: str) -> str:
        return self.lexer.escape_string(s)
    
    # ===== GERAÇÃO =====
    def generate(self, source: str) -> str:
        """Método principal para gerar código Swift"""
        tree = self.lexer.analyze(source)
        self.type_inferencer.infer(tree)
        
        # Adiciona header
        self.emit("import Foundation")
        self.emit("")
        self.emit("// Transpilado de Python para Swift")
        self.emit("// Gerado automaticamente - pode necessitar ajustes manuais")
        self.emit("")
        
        for node in tree.body:
            if self._is_main_guard(node):
                for stmt in node.body:
                    self.visit(stmt)
            else:
                self.visit(node)
        
        if self.warnings:
            self.emit("")
            self.emit("// ⚠️  AVISOS DE TRANSPILAÇÃO:")
            for w in self.warnings:
                self.emit(f"// {w}")
        
        return "\n".join(self.lines) + "\n"
    
    def _is_main_guard(self, node: ast.AST) -> bool:
        """Verifica se é if __name__ == "__main__":"""
        return (isinstance(node, ast.If) and
                isinstance(node.test, ast.Compare) and
                isinstance(node.test.left, ast.Name) and
                node.test.left.id == "__name__")
    
    # ===== VISITANTES - ESTRUTURAS =====
    
    def visit_Module(self, node: ast.Module):
        pass 
        
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.name
            if name in ('math', 'random', 'datetime', 'json'):
                self.emit("import Foundation")
            elif name == 're':
                self.emit("import Foundation  // Use NSRegularExpression")
            else:
                self.emit(f"// import {name}  // ⚠️ Mapeamento manual necessário")
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        names = [alias.name for alias in node.names]
        self.emit(f"// from {module} import {', '.join(names)}  // ⚠️ Mapear manualmente")
    
    def visit_ClassDef(self, node: ast.ClassDef):
        bases = []
        for b in node.bases:
            if isinstance(b, ast.Name):
                bases.append(b.id)
            else:
                bases.append(self._expr_str(b))

        base_str = f": {', '.join(bases)}" if bases else ""
        self.emit(f"class {node.name}{base_str} {{")

        self.indent_level += 1
        prev_class = self.current_class
        self.current_class = node.name
        self.symbol_table.push_scope(f"class:{node.name}")

        # MELHORIA: Traduz atributos de classe
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        self.emit(f"static var {target.id}: {self._infer_type(stmt.value)} = {self._expr_str(stmt.value)}")
            elif isinstance(stmt, ast.FunctionDef):
                self.visit(stmt)

        self.symbol_table.pop_scope()
        self.current_class = prev_class
        self.indent_level -= 1
        self.emit("}")
        self.emit("")

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.symbol_table.push_scope(f"func:{node.name}")

        args = []
        for arg in node.args.args:
            if arg.arg == 'self':
                continue
            sig = self.type_inferencer.func_signatures.get(node.name, {})

            arg_type = sig.get(arg.arg, 'Any')

            if arg_type == 'Any':
                if arg.arg in ('n', 'num', 'number', 'count', 'index', 'i', 'j', 'k'):
                    arg_type = 'Int'
                elif arg.arg in ('x', 'y', 'value', 'val', 'amount'):
                    arg_type = 'Double'

            args.append(f"_{arg.arg}: {arg_type}")

        arglist = ', '.join(args)

        sig = self.type_inferencer.func_signatures.get(node.name, {})
        return_type = sig.get('return', 'Void')

        # CORREÇÃO SIMPLIFICADA: Para funções com nome sugestivo de inteiros, força Int
        if return_type == 'Double' and self._looks_like_int_function(node):
            return_type = 'Int'

        # CORREÇÃO: Se a função opera apenas com inteiros, força Int
        # Adiciona logs para depuração
        import logging
        logging.debug(f"Analisando tipo de retorno para a função '{node.name}'. Tipo inferido: {return_type}")

        if return_type == 'Double' and self._looks_like_int_function(node):
            logging.debug(f"Função '{node.name}' parece operar com inteiros. Alterando tipo de retorno para 'Int'.")
            return_type = 'Int'

        if return_type in ['Any', 'Double']:
            try:
                if self._function_uses_only_ints(node):
                    logging.debug(f"Função '{node.name}' usa apenas inteiros. Alterando tipo de retorno para 'Int'.")
                    return_type = 'Int'
            except Exception as e:
                logging.exception(f"Erro ao verificar se a função '{node.name}' usa apenas inteiros: {e}")

        ret_annotation = f" -> {return_type}" if return_type != 'Void' else ""

        # MELHORIA: Suporte para métodos de classe
        if any(isinstance(decorator, ast.Name) and decorator.id == 'classmethod' for decorator in node.decorator_list):
            self.emit(f"class func {node.name}({arglist}){ret_annotation} {{")
        else:
            self.emit(f"func {node.name}({arglist}){ret_annotation} {{")

        self.indent_level += 1
        for stmt in node.body:
            self.visit(stmt)
        self.indent_level -= 1
        self.emit("}")

        self.symbol_table.pop_scope()

    def visit_Return(self, node: ast.Return):
        if node.value:
            # MELHORIA: Gera código idiomático para retornos
            return_expr = self._expr_str(node.value)
            if return_expr == 'None':
                self.emit("return")
            else:
                self.emit(f"return {return_expr}")
        else:
            self.emit("return")
    
    # ===== VISITANTES - ATRIBUIÇÕES =====
    
    def visit_Assign(self, node: ast.Assign):
        """Transpila atribuições"""
        value_str = self._expr_str(node.value)
        
        for target in node.targets:
            if isinstance(target, ast.Tuple):
                self._handle_tuple_assign(target, node.value)
                continue
            
            if isinstance(target, ast.Attribute):
                if isinstance(target.value, ast.Name) and target.value.id == 'self':
                    self.emit(f"self.{target.attr} = {value_str}")
                else:
                    self.emit(f"{self._expr_str(target.value)}.{target.attr} = {value_str}")
                continue
            
            if isinstance(target, ast.Name):
                name = target.id
                self._emit_assignment(name, value_str, node)
                continue
            
            if isinstance(target, ast.Subscript):
                self.emit(f"{self._expr_str(target)} = {value_str}")
                continue
            
            self.emit(f"{self._expr_str(target)} = {value_str}")
    
    def _handle_tuple_assign(self, target: ast.Tuple, value: ast.AST):
        """Lida com desempacotamento de tuplas"""
        if not isinstance(value, ast.Tuple):
            self.warn("Desempacotamento de tupla com valor não-tupla pode não funcionar")
            return
        
        if len(target.elts) == 2 and len(value.elts) == 2:
            swap_detected = self._try_emit_swap(target.elts, value.elts)
            if swap_detected:
                return
        
        for left, right in zip(target.elts, value.elts):
            left_str = self._expr_str(left)
            right_str = self._expr_str(right)
            
            if isinstance(left, ast.Name):
                self._emit_assignment(left.id, right_str, None)
            else:
                self.emit(f"{left_str} = {right_str}")
    
    def _try_emit_swap(self, left_elts: List[ast.AST], right_elts: List[ast.AST]) -> bool:
        """Tenta detectar e emitir padrão de swap"""
        try:
            L0, L1 = left_elts
            R0, R1 = right_elts
            
            if not all(isinstance(x, ast.Subscript) for x in [L0, L1, R0, R1]):
                return False
            
            if not (isinstance(L0.value, ast.Name) and isinstance(L1.value, ast.Name)):
                return False
            
            if L0.value.id != L1.value.id:
                return False
            
            i0 = self._expr_str(L0.slice)
            i1 = self._expr_str(L1.slice)
            r0 = self._expr_str(R0.slice)
            r1 = self._expr_str(R1.slice)
            
            if i0 == r1 and i1 == r0:
                self.emit(f"{L0.value.id}.swapAt({i0}, {i1})")
                return True
        except:
            pass
        
        return False
    
    def _emit_assignment(self, name: str, value: str, node: Optional[ast.Assign]):
        """Emite atribuição com declaração apropriada"""
        if not self.symbol_table.is_declared_in_current_scope(name):
            inferred_type = self.type_inferencer.var_types.get(name, 'Any')
            
            is_constant = (node and isinstance(node.value, ast.Constant))
            decl = 'let' if is_constant else 'var'
            
            if inferred_type != 'Any':
                self.emit(f"{decl} {name}: {inferred_type} = {value}")
            else:
                self.emit(f"{decl} {name} = {value}")
            
            self.symbol_table.declare(name, Symbol(name, inferred_type, not is_constant))
        else:
            self.emit(f"{name} = {value}")
    
    def visit_AugAssign(self, node: ast.AugAssign):
        """Atribuição composta (+=, -=, etc)"""
        target = self._expr_str(node.target)
        op = self._augop_symbol(node.op)
        value = self._expr_str(node.value)
        self.emit(f"{target} {op}= {value}")
    
    # ===== VISITANTES - CONTROLE DE FLUXO =====
    
    def visit_If(self, node: ast.If):
        """Transpila if/elif/else com indentação correta"""
        cond = self._expr_str(node.test)
        self.emit(f"if {cond} {{")
        
        self.indent_level += 1
        for stmt in node.body:
            self.visit(stmt)
        self.indent_level -= 1
        
        if node.orelse:
            self._handle_orelse(node.orelse)
        else:
            self.emit("}")
    
    def _handle_orelse(self, orelse: List[ast.stmt]):
        """Lida com else e elif recursivamente para garantir indentação correta"""
        if not orelse:
            return
        
        # Verifica se é um elif
        if len(orelse) == 1 and isinstance(orelse[0], ast.If):
            elif_node = orelse[0]
            cond = self._expr_str(elif_node.test)
            self.emit(f"}} else if {cond} {{")
            
            self.indent_level += 1
            for stmt in elif_node.body:
                self.visit(stmt)
            self.indent_level -= 1
            
            # Continua a cadeia
            if elif_node.orelse:
                self._handle_orelse(elif_node.orelse)
            else:
                self.emit("}")
        else:
            # Else simples
            self.emit("} else {")
            self.indent_level += 1
            for stmt in orelse:
                self.visit(stmt)
            self.indent_level -= 1
            self.emit("}")

    def visit_For(self, node: ast.For):
        """Transpila loops for"""
        target = self._expr_str(node.target)
        
        if self._is_range_call(node.iter):
            self._emit_range_for(target, node.iter, node.body)
            return
        
        if isinstance(node.iter, ast.List):
            elements = ', '.join(self._expr_str(e) for e in node.iter.elts)
            self.emit(f"for {target} in [{elements}] {{")
        else:
            self.emit(f"for {target} in {self._expr_str(node.iter)} {{")
        
        self.indent_level += 1
        for stmt in node.body:
            self.visit(stmt)
        self.indent_level -= 1
        self.emit("}")
        
        if node.orelse:
            self.warn("for-else não tem equivalente direto em Swift", node)
    
    def _is_range_call(self, node: ast.AST) -> bool:
        """Verifica se é uma chamada range()"""
        return (isinstance(node, ast.Call) and
                isinstance(node.func, ast.Name) and
                node.func.id == 'range')
    
    def _emit_range_for(self, target: str, range_call: ast.Call, body: List[ast.stmt]):
        """Emite for com range otimizado"""
        args = range_call.args
        
        if len(args) == 1:
            stop = self._expr_str(args[0])
            self.emit(f"for {target} in 0..<{stop} {{")
        elif len(args) == 2:
            start = self._expr_str(args[0])
            stop = self._expr_str(args[1])
            self.emit(f"for {target} in {start}..<{stop} {{")
        elif len(args) == 3:
            start = self._expr_str(args[0])
            stop = self._expr_str(args[1])
            step = self._expr_str(args[2])
            self.emit(f"for {target} in stride(from: {start}, to: {stop}, by: {step}) {{")
        else:
            self.emit(f"for {target} in {self._expr_str(range_call)} {{")
        
        self.indent_level += 1
        for stmt in body:
            self.visit(stmt)
        self.indent_level -= 1
        self.emit("}")
    
    def visit_While(self, node: ast.While):
        """Transpila loops while"""
        cond = self._expr_str(node.test)
        self.emit(f"while {cond} {{")
        
        self.indent_level += 1
        for stmt in node.body:
            self.visit(stmt)
        self.indent_level -= 1
        
        self.emit("}")
        
        if node.orelse:
            self.warn("while-else não tem equivalente direto em Swift", node)
            self.emit("// while-else original:")
            self.indent_level += 1
            for stmt in node.orelse:
                self.visit(stmt)
            self.indent_level -= 1
    
    def visit_Break(self, node: ast.Break):
        self.emit("break")
    
    def visit_Continue(self, node: ast.Continue):
        self.emit("continue")
    
    def visit_Pass(self, node: ast.Pass):
        self.emit("// pass")
    
    # ===== VISITANTES - EXPRESSÕES E TRY/EXCEPT =====
    
    def visit_Expr(self, node: ast.Expr):
        self.emit(self._expr_str(node.value))
    
    def visit_Try(self, node: ast.Try):
        
        if self._try_special_input_pattern(node):
            return
        
        if node.handlers:
            self.emit("do {")
            self.indent_level += 1
            for stmt in node.body:
                self.visit(stmt)
            self.indent_level -= 1
            
            for handler in node.handlers:
                exc_type = handler.type
                if exc_type and isinstance(exc_type, ast.Name):
                    self.emit(f"}} catch let error as {exc_type.id} {{")
                else:
                    self.emit("} catch {")
                
                self.indent_level += 1
                for stmt in handler.body:
                    self.visit(stmt)
                self.indent_level -= 1
            
            self.emit("}")
        else:
            self.warn("try sem except handlers", node)
            self.indent_level += 1
            for stmt in node.body:
                self.visit(stmt)
            self.indent_level -= 1
    
    def _try_special_input_pattern(self, node: ast.Try) -> bool:
        """Detecta e transpila padrão int(input())"""
        for stmt in node.body:
            if not isinstance(stmt, ast.Assign):
                continue
            
            if not isinstance(stmt.value, ast.Call):
                continue
            
            int_call = stmt.value
            if not (isinstance(int_call.func, ast.Name) and int_call.func.id == 'int'):
                continue
            
            if not int_call.args:
                continue
            
            input_call = int_call.args[0]
            if not (isinstance(input_call, ast.Call) and
                    isinstance(input_call.func, ast.Name) and
                    input_call.func.id == 'input'):
                continue
            
            target = stmt.targets[0]
            name = self._expr_str(target)
            
            prompt = '""'
            if input_call.args and isinstance(input_call.args[0], ast.Constant):
                prompt_text = self.escape_string(str(input_call.args[0].value))
                prompt = f'"{prompt_text}"'
            
            self.emit(f'print({prompt}, terminator: "")')
            self.emit(f"if let line = readLine(), let {name} = Int(line) {{")
            
            self.indent_level += 1
            for s in node.body:
                if s is not stmt:
                    self.visit(s)
            self.indent_level -= 1
            
            if node.handlers:
                self.emit("} else {")
                self.indent_level += 1
                for handler in node.handlers:
                    for s in handler.body:
                        self.visit(s)
                self.indent_level -= 1
            
            self.emit("}")
            return True
        
        return False
    
    # ===== EXPRESSÕES =====
    
    def _expr_str(self, node: ast.AST) -> str:
        if node is None:
            return 'nil'
        
        method = getattr(self, f"_expr_{node.__class__.__name__}", None)
        if method:
            return method(node)
        
        self.warn(f"Expressão não suportada: {node.__class__.__name__}", node)
        return '/* expressão não suportada */'
    
    def _expr_Name(self, node: ast.Name) -> str:
        if node.id == 'True':
            return 'true'
        if node.id == 'False':
            return 'false'
        if node.id == 'None':
            return 'nil'
        return node.id
    
    def _expr_Constant(self, node: ast.Constant) -> str:
        v = node.value
        
        if isinstance(v, bool):
            return 'true' if v else 'false'
        if v is None:
            return 'nil'
        if isinstance(v, int):
            return str(v)
        if isinstance(v, float):
            return str(v)
        if isinstance(v, str):
            return f'"{self.escape_string(v)}"'
        
        return 'nil'
    
    def _expr_Attribute(self, node: ast.Attribute) -> str:
        value = self._expr_str(node.value)
        return f"{value}.{node.attr}"
    
    def _expr_JoinedStr(self, node: ast.JoinedStr) -> str:
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(self.escape_string(value.value))
            elif isinstance(value, ast.FormattedValue):
                parts.append(f"\\({self._expr_str(value.value)})")
            else:
                parts.append("\\(/* valor desconhecido */)")
        
        return '"' + ''.join(parts) + '"'
    
    def _expr_BinOp(self, node: ast.BinOp) -> str:
        """Operações binárias"""
        left = self._expr_str(node.left)
        right = self._expr_str(node.right)
        op = self._binop_symbol(node.op)
        
        # Correção para FloorDiv (//)
        if isinstance(node.op, ast.FloorDiv):
             return f"Int(Double({left}) / Double({right}))"
        
        # Correção para Pow (**)
        if isinstance(node.op, ast.Pow):
             return f"pow({left}, {right})"
        
        return f"({left} {op} {right})"
    
    def _expr_UnaryOp(self, node: ast.UnaryOp) -> str:
        operand = self._expr_str(node.operand)
        
        if isinstance(node.op, ast.Not):
            return f"!({operand})"
        elif isinstance(node.op, ast.USub):
            return f"-({operand})"
        elif isinstance(node.op, ast.UAdd):
            return operand
        
        return f"/* unary op */ {operand}"
    
    def _expr_BoolOp(self, node: ast.BoolOp) -> str:
        values = [self._expr_str(v) for v in node.values]
        op = ' && ' if isinstance(node.op, ast.And) else ' || '
        return '(' + op.join(values) + ')'
    
    def _expr_Compare(self, node: ast.Compare) -> str:
        parts = []
        left = self._expr_str(node.left)
        
        for op, comparator in zip(node.ops, node.comparators):
            right = self._expr_str(comparator)
            symbol = self._cmpop_symbol(op)
            
            # Tratamento de 'in'/'not in'
            if type(op) in (ast.In, ast.NotIn):
                 if symbol == 'in':
                     parts.append(f"{right}.contains({left})")
                 else:
                     parts.append(f"!({right}.contains({left}))")
            else:
                parts.append(f"{left} {symbol} {right}")
            
            left = right
        
        return ' && '.join(parts) if len(parts) > 1 else parts[0]
    
    def _expr_Call(self, node: ast.Call) -> str:
        if isinstance(node.func, ast.Name):
            return self._handle_builtin_call(node)
        
        if isinstance(node.func, ast.Attribute):
            return self._handle_method_call(node)
        
        func = self._expr_str(node.func)
        args = ', '.join(self._expr_str(a) for a in node.args)
        return f"{func}({args})"
    
    def _handle_builtin_call(self, node: ast.Call) -> str:
        fname = node.func.id
        args = [self._expr_str(a) for a in node.args]
        
        if fname == 'print':
            return f"print({', '.join(args)})"
        
        if fname == 'len' and len(args) == 1:
            return f"{args[0]}.count"
        
        if fname == 'sum' and len(args) == 1:
            list_type = self.type_inferencer._infer_expr_type(node.args[0])
            initial_value = '0.0' if list_type and 'Double' in list_type else '0'
            return f"{args[0]}.reduce({initial_value}, +)"
        
        if fname == 'min' and len(args) >= 1:
            if len(args) == 1:
                return f"{args[0]}.min() ?? 0"
            return f"min({', '.join(args)})"
        
        if fname == 'max' and len(args) >= 1:
            if len(args) == 1:
                return f"{args[0]}.max() ?? 0"
            return f"max({', '.join(args)})"
        
        if fname == 'abs' and len(args) == 1:
            return f"abs({args[0]})"
        
        if fname == 'sorted' and len(args) == 1:
            return f"{args[0]}.sorted()"
        
        if fname == 'reversed' and len(args) == 1:
            return f"Array({args[0]}.reversed())"
        
        if fname == 'range':
            if len(args) == 1:
                return f"0..<{args[0]}"
            elif len(args) == 2:
                return f"{args[0]}..<{args[1]}"
        
        if fname == 'str' and len(args) == 1:
            return f"String({args[0]})"
        
        if fname == 'int' and len(args) == 1:
            return f"Int({args[0]}) ?? 0" 
        
        if fname == 'float' and len(args) == 1:
            return f"Double({args[0]}) ?? 0.0"
        
        if fname == 'list':
            if len(args) == 0:
                return "[]"
            return f"Array({args[0]})"
        
        if fname == 'dict':
            return "[:]"
        
        if fname == 'enumerate' and len(args) == 1:
            return f"{args[0]}.enumerated()"
        
        if fname == 'zip' and len(args) >= 2:
            return f"zip({', '.join(args)})"
        
        if fname == 'map' and len(args) == 2:
            return f"{args[1]}.map({args[0]})"
        
        if fname == 'filter' and len(args) == 2:
            return f"{args[1]}.filter({args[0]})"
        
        if fname == 'any' and len(args) == 1:
            return f"{args[0]}.contains(where: {{ $0 }})"
        
        if fname == 'all' and len(args) == 1:
            return f"{args[0]}.allSatisfy({{ $0 }})"

        return f"{fname}({', '.join(args)})"
    
    def _handle_method_call(self, node: ast.Call) -> str:
        obj = self._expr_str(node.func.value)
        method = node.func.attr
        args = [self._expr_str(a) for a in node.args]
        
        # String methods
        if method == 'lower':
            return f"{obj}.lowercased()"
        if method == 'upper':
            return f"{obj}.uppercased()"
        if method == 'strip':
            return f"{obj}.trimmingCharacters(in: .whitespacesAndNewlines)"
        if method == 'replace' and len(args) == 2:
            return f"{obj}.replacingOccurrences(of: {args[0]}, with: {args[1]})"
        if method == 'split':
            if len(args) == 0:
                return f"{obj}.split(separator: \" \").map(String.init)"
            return f"{obj}.split(separator: {args[0]}).map(String.init)"
        if method == 'join' and len(args) == 1:
            return f"{args[0]}.joined(separator: {obj})"
        if method == 'startswith' and len(args) == 1:
            return f"{obj}.hasPrefix({args[0]})"
        if method == 'endswith' and len(args) == 1:
            return f"{obj}.hasSuffix({args[0]})"
        
        # List methods
        if method == 'append' and len(args) == 1:
            return f"{obj}.append({args[0]})"
        if method == 'extend' and len(args) == 1:
            return f"{obj}.append(contentsOf: {args[0]})"
        if method == 'insert' and len(args) == 2:
            return f"{obj}.insert({args[1]}, at: {args[0]})"
        if method == 'remove' and len(args) == 1:
            return f"{obj}.removeAll(where: {{ $0 == {args[0]} }})" 
        if method == 'pop':
            if len(args) == 0:
                return f"{obj}.removeLast()"
            return f"{obj}.remove(at: {args[0]})"
        
        # Dict methods
        if method == 'get' and len(args) >= 1:
            default = args[1] if len(args) > 1 else 'nil'
            return f"({obj}[{args[0]}] ?? {default})"
        if method == 'keys':
            return f"Array({obj}.keys)"
        if method == 'values':
            return f"Array({obj}.values)"
        if method == 'items':
            return f"Array({obj})"
        
        return f"{obj}.{method}({', '.join(args)})"
    
    def _expr_List(self, node: ast.List) -> str:
        elements = ', '.join(self._expr_str(e) for e in node.elts)
        return f"[{elements}]"
    
    def _expr_ListComp(self, node: ast.ListComp) -> str:
        if not node.generators:
            return "[]"
        
        gen = node.generators[0]
        
        if len(node.generators) > 1:
            self.warn("Compreensão de lista com múltiplos for não suportada", node)
            return "[]"
        
        iter_expr = self._expr_str(gen.iter)
        target = self._expr_str(gen.target)
        elt_expr = self._expr_str(node.elt)
        
        if target in elt_expr:
            elt_expr = elt_expr.replace(target, "$0")
        
        if gen.ifs:
            cond = self._expr_str(gen.ifs[0])
            if target in cond:
                cond = cond.replace(target, "$0")
            return f"{iter_expr}.filter{{ {cond} }}.map{{ {elt_expr} }}"
        
        if elt_expr == target or elt_expr == "$0":
            return iter_expr  
        return f"{iter_expr}.map{{ {elt_expr} }}"
    
    def _expr_Dict(self, node: ast.Dict) -> str:
        if not node.keys:
            return "[:]"
        
        pairs = []
        for k, v in zip(node.keys, node.values):
            key = self._expr_str(k)
            val = self._expr_str(v)
            pairs.append(f"{key}: {val}")
        
        return f"[{', '.join(pairs)}]"
    
    def _expr_Subscript(self, node: ast.Subscript) -> str:
        value = self._expr_str(node.value)
        
        if isinstance(node.slice, ast.Slice):
            return self._handle_slice(value, node.slice)
        
        index = self._expr_str(node.slice)
        return f"{value}[{index}]"
    
    def _handle_slice(self, value: str, slice_node: ast.Slice) -> str:
        if slice_node.step:
            if isinstance(slice_node.step, ast.Constant) and slice_node.step.value == -1:
                if slice_node.lower is None and slice_node.upper is None:
                    return f"Array({value}.reversed())" 
                else:
                    self.warn("Slice com step -1 e bounds não totalmente suportado", slice_node)
                    return f"Array({value}.reversed())"
            else:
                self.warn("Slice com step diferente de -1 não suportado. Use um loop `stride` manual.", slice_node)
                return f"/* Slice com step não suportado */"
        
        lower_present = slice_node.lower is not None
        upper_present = slice_node.upper is not None

        if not lower_present and not upper_present:
            return value
        
        if not lower_present:
            upper = self._expr_str(slice_node.upper)
            return f"{value}[..<{upper}]"
        
        if not upper_present:
            lower = self._expr_str(slice_node.lower)
            return f"{value}[{lower}...]"
        
        lower = self._expr_str(slice_node.lower)
        upper = self._expr_str(slice_node.upper)
        return f"{value}[{lower}..<{upper}]"
    
    def _expr_Tuple(self, node: ast.Tuple) -> str:
        elements = ', '.join(self._expr_str(e) for e in node.elts)
        return f"({elements})"
    
    def _expr_IfExp(self, node: ast.IfExp) -> str:
        cond = self._expr_str(node.test)
        true_val = self._expr_str(node.body)
        false_val = self._expr_str(node.orelse)
        return f"({cond} ? {true_val} : {false_val})"
    
    def _expr_Lambda(self, node: ast.Lambda) -> str:
        args = [a.arg for a in node.args.args]
        body = self._expr_str(node.body)
        
        if not args:
            return f"{{ {body} }}"
        
        arg_list_with_type = ', '.join(f"{a}: Any" for a in args) 
        
        return f"{{ {arg_list_with_type} in return {body} }}"
    
    def _expr_Set(self, node: ast.Set) -> str:
        elements = ', '.join(self._expr_str(e) for e in node.elts)
        return f"Set([{elements}])"
    
    # ===== AUXILIARES PARA OPERADORES =====
    def _binop_symbol(self, op: ast.AST) -> str:
        mapping = {
            ast.Add: '+',
            ast.Sub: '-',
            ast.Mult: '*',
            ast.Div: '/',
            ast.Mod: '%',
        }
        symbol = mapping.get(type(op), '/*op*/')
        return symbol
    
    def _cmpop_symbol(self, op: ast.AST) -> str:
        mapping = {
            ast.Eq: '==',
            ast.NotEq: '!=',
            ast.Lt: '<',
            ast.LtE: '<=',
            ast.Gt: '>',
            ast.GtE: '>=',
            ast.Is: '===',
            ast.IsNot: '!==',
        }
        symbol = mapping.get(type(op), '/*cmp*/')
        return symbol
    
    def _augop_symbol(self, op: ast.AST) -> str:
        return self._binop_symbol(op)
    
    # ===== FALLBACK =====
    def generic_visit(self, node: ast.AST):
        self.warn(f"Nó não tratado: {node.__class__.__name__}", node)

# ===== FUNÇÃO DE CONVENIÊNCIA =====
def transpile(source: str) -> str:
    """
    Transpila código Python para Swift.
    """
    transpiler = PyToSwiftTranspiler()
    return transpiler.generate(source)