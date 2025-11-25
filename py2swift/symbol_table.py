from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class Symbol:
    """Representa um símbolo (variável, função, etc)"""
    name: str
    type_hint: str = "Any"
    is_mutable: bool = True
    scope: str = "local"

class SymbolTable:
    """Gerencia escopos e símbolos"""
    def __init__(self):
        self.scopes: List[Dict[str, Symbol]] = [{}]  # Global scope
        self.scope_names: List[str] = ["global"]
    
    def push_scope(self, name: str = "local"):
        self.scopes.append({})
        self.scope_names.append(name)
    
    def pop_scope(self):
        if len(self.scopes) > 1:
            self.scopes.pop()
            self.scope_names.pop()
    
    def declare(self, name: str, symbol: Symbol):
        self.scopes[-1][name] = symbol
    
    def lookup(self, name: str) -> Optional[Symbol]:
        # Busca do escopo atual para o global
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None
    
    def is_declared_in_current_scope(self, name: str) -> bool:
        return name in self.scopes[-1]