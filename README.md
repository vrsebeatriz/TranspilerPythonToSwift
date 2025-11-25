# Py2Swift Transpiler

Um transpilador de Python para Swift que converte código Python em código Swift funcional, mantendo a lógica e estrutura original.

## 📋 Sumário

- [Visão Geral](#visão-geral)
- [Funcionalidades Suportadas](#funcionalidades-suportadas)
- [Limitações e Não Suportados](#limitações-e-não-suportados)
- [Instalação e Uso](#instalação-e-uso)
- [Tokens Reconhecidos](#tokens-reconhecidos)
- [Exemplos de Conversão](#exemplos-de-conversão)
- [API Web](#api-web)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Contribuindo](#contribuindo)

## 🚀 Visão Geral

O Py2Swift é um transpilador que analisa código Python e gera código Swift equivalente. Ele realiza:

- **Análise Léxica e Sintática** usando a AST do Python
- **Inferência de Tipos** para declarações automáticas de variáveis
- **Tradução de Construções** de Python para Swift
- **Geração de Código** com indentação correta e comentários

## ✅ Funcionalidades Suportadas

### 🏗️ Estruturas Básicas
- ✅ Funções e métodos
- ✅ Classes e herança
- ✅ Variáveis e constantes (`var`/`let`)
- ✅ Importações básicas

### 🔄 Controle de Fluxo
- ✅ Condicionais: `if`, `elif`, `else`
- ✅ Loops: `for`, `while`
- ✅ `break`, `continue`
- ✅ Tratamento de exceções: `try`, `except`

### 📊 Tipos de Dados
- ✅ `int` → `Int`
- ✅ `float` → `Double`
- ✅ `str` → `String`
- ✅ `bool` → `Bool`
- ✅ `list` → `Array`
- ✅ `dict` → `Dictionary`
- ✅ `tuple` → Tupla Swift
- ✅ `set` → `Set`

### 🔧 Operações
- ✅ Operadores aritméticos: `+`, `-`, `*`, `/`, `%`
- ✅ Operadores de comparação: `==`, `!=`, `<`, `>`, `<=`, `>=`
- ✅ Operadores lógicos: `and`, `or`, `not`
- ✅ Operadores de atribuição: `=`, `+=`, `-=`, etc.

### 📚 Built-ins e Métodos
- ✅ `print()`
- ✅ `len()` → `.count`
- ✅ `range()` → `..<` e `stride()`
- ✅ `sum()`, `min()`, `max()`
- ✅ Métodos de string: `.lower()`, `.upper()`, `.strip()`, etc.
- ✅ Métodos de lista: `.append()`, `.insert()`, `.pop()`, etc.
- ✅ Métodos de dicionário: `.keys()`, `.values()`, `.items()`

### 🎯 Funcionalidades Avançadas
- ✅ Compreensões de lista
- ✅ Desempacotamento de tuplas
- ✅ Detecção de swap de variáveis
- ✅ Padrão `int(input())` com tratamento de erro
- ✅ Funções lambda
- ✅ F-strings

## ❌ Limitações e Não Suportados

### 🚫 Não Suportados Atualmente
- ❌ Decoradores
- ❌ Geradores e `yield`
- ❌ Expressões regulares avançadas
- ❌ Módulos específicos do Python (`numpy`, `pandas`, etc.)
- ❌ Metaclasses
- ❌ Descriptors
- ❌ Context managers (`with` statement)
- ❌ Assincronia (`async`/`await`)

### ⚠️ Funcionalidades Parciais
- ⚠️ Slices com step diferente de -1
- ⚠️ `for-else` e `while-else` (gera aviso)
- ⚠️ Múltiplas compreensões de lista
- ⚠️ Módulos importados (requer mapeamento manual)

## 🛠️ Instalação e Uso

### Requisitos
```bash
Python 3.8+
Flask (para a interface web)
```

### Uso como Biblioteca
```python
from py2swift import transpile

python_code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

print(factorial(5))
"""

swift_code = transpile(python_code)
print(swift_code)
```

### Interface Web
```bash
python webapp.py
```
Acesse: `http://127.0.0.1:5000`

## 🔤 Tokens Reconhecidos

### Palavras-chave Python → Swift
| Python | Swift | Notas |
|--------|-------|-------|
| `def` | `func` | |
| `class` | `class` | |
| `if` | `if` | |
| `elif` | `else if` | |
| `else` | `else` | |
| `for` | `for` | |
| `while` | `while` | |
| `return` | `return` | |
| `True` | `true` | |
| `False` | `false` | |
| `None` | `nil` | |
| `and` | `&&` | |
| `or` | `\|\|` | |
| `not` | `!` | |
| `in` | `.contains()` | |
| `is` | `===` | |

### Operadores
| Python | Swift |
|--------|-------|
| `+`, `-`, `*`, `/` | `+`, `-`, `*`, `/` |
| `//` | `Int(Double(a) / Double(b))` |
| `**` | `pow()` |
| `%` | `%` |
| `==`, `!=` | `==`, `!=` |
| `<`, `>`, `<=`, `>=` | `<`, `>`, `<=`, `>=` |

### Built-in Functions
| Python | Swift |
|--------|-------|
| `len(x)` | `x.count` |
| `sum(x)` | `x.reduce(0, +)` |
| `range(n)` | `0..<n` |
| `range(a, b)` | `a..<b` |
| `str(x)` | `String(x)` |
| `int(x)` | `Int(x) ?? 0` |
| `float(x)` | `Double(x) ?? 0.0` |

## 📝 Exemplos de Conversão

### Exemplo 1: Fatorial
**Python:**
```python
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

print(factorial(5))
```

**Swift:**
```swift
import Foundation

func factorial(_ n: Int) -> Int {
    if n <= 1 {
        return 1
    }
    return n * factorial(n - 1)
}

print(factorial(5))
```

### Exemplo 2: Bubble Sort
**Python:**
```python
nums = [5, 3, 8, 2, 1]

for i in range(len(nums)):
    for j in range(len(nums) - 1):
        if nums[j] > nums[j + 1]:
            nums[j], nums[j + 1] = nums[j + 1], nums[j]

print(nums)
```

**Swift:**
```swift
import Foundation

var nums = [5, 3, 8, 2, 1]

for i in 0..<nums.count {
    for j in 0..<nums.count - 1 {
        if nums[j] > nums[j + 1] {
            nums.swapAt(j, j + 1)
        }
    }
}

print(nums)
```

### Exemplo 3: Entrada de Usuário
**Python:**
```python
try:
    age = int(input("Digite sua idade: "))
    print(f"Você tem {age} anos")
except ValueError:
    print("Idade inválida!")
```

**Swift:**
```swift
import Foundation

print("Digite sua idade: ", terminator: "")
if let line = readLine(), let age = Int(line) {
    print("Você tem \\(age) anos")
} else {
    print("Idade inválida!")
}
```

## 🌐 API Web

### Endpoints

#### `GET /`
- **Descrição**: Interface web do transpilador
- **Resposta**: HTML da aplicação

#### `POST /transpile`
- **Descrição**: Transpila código Python para Swift
- **Body**: `{"source": "código python"}`
- **Resposta**: 
```json
{
    "success": true,
    "output": "código swift"
}
```
ou
```json
{
    "success": false,
    "error": "mensagem de erro"
}
```

#### `GET /health`
- **Descrição**: Verificação de saúde da API
- **Resposta**: 
```json
{
    "status": "healthy",
    "service": "Python to Swift Transpiler API"
}
```

## 📁 Estrutura do Projeto

```
py2swift/
├── __init__.py              # Inicialização do pacote
├── transpiler.py           # Transpilador principal
├── lexer.py               # Análise léxica
├── type_inference.py      # Inferência de tipos
├── symbol_table.py        # Tabela de símbolos
├── exceptions.py          # Exceções personalizadas
webapp.py                  # Aplicação Flask
templates/
└── index.html            # Interface web
```

### Módulos Principais

1. **`transpiler.py`** - Núcleo do transpilador, visita nós da AST
2. **`lexer.py`** - Análise léxica e escape de strings
3. **`type_inference.py`** - Inferência de tipos para variáveis e funções
4. **`symbol_table.py`** - Gerenciamento de escopos e símbolos
5. **`exceptions.py`** - Exceções específicas do transpilador

## 🐛 Problemas Conhecidos

1. **Indentação**: Em casos complexos, pode requerer ajustes manuais
2. **Tipos Complexos**: Inferência de tipos para estruturas aninhadas é limitada
3. **Performance**: Código gerado pode não ser otimizado
4. **Bibliotecas**: Módulos Python específicos requerem implementação manual em Swift

### Áreas para Melhoria
- [ ] Suporte a mais built-ins do Python
- [ ] Melhor inferência de tipos
- [ ] Otimização do código gerado
- [ ] Suporte a mais padrões de código
- [ ] Tratamento de módulos externos

## ⚠️ Aviso

Este transpilador gera código Swift funcional, mas pode requerer ajustes manuais para:
- Otimizações de performance
- Estilo de código Swift idiomático
- Casos de borda específicos
- Integração com frameworks Swift

Sempre revise e teste o código gerado antes de usar em produção.