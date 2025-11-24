# Transpilador Python to Swift
Este é um projeto acadêmico de um Transpilador de Código-Fonte desenvolvido em Python, que converte código Python 3.x para a linguagem de programação Swift. O objetivo é demonstrar a arquitetura e os desafios na conversão de uma linguagem de tipagem dinâmica (Python) para uma de tipagem estática (Swift).

## Introdução

O **transpilador** utiliza a Árvore de Sintaxe Abstrata (AST) do Python para analisar o código-fonte e, em seguida, gera uma representação sintática e semanticamente equivalente em Swift. O foco principal é a **inferência de tipos** para garantir a segurança de código, característica fundamental do Swift.

## Funcionalidades Atuais 

A versão atual do Transpilador implementa as seguintes conversões e otimizações:

### 1. Sistema de Tipagem Inteligente

| Recurso Python | Conversão para Swift | Notas |
| :--- | :--- | :--- |
| Variáveis (`var/let`) | Uso de `var` ou `let` | Determinado pela inferência de constante (`let`) ou mutabilidade (`var`). |
| Tipos Numéricos | `Int`, `Double` | Promoção automática para `Double` em operações mistas. |
| Dicionário Heterogêneo | `[String: Any]` | Inferência correta para tipos de valor mistos (ex: `String` e `[Double]`). |
| Listas (Arrays) | `[Int]`, `[String]`, `[Any]` | Inferência do tipo de elemento do Array. |

### 2. Estruturas de Controle e Loops

| Recurso Python | Conversão para Swift |
| :--- | :--- |
| `if/elif/else` | `if/else if/else` | Estruturas de controle padrão com indentação correta. |
| `for x in range(n)` | `for x in 0..<n` | Otimização para o operador de *Range* (meio aberto) do Swift. |
| `for x in range(a, b)` | `for x in a..<b` | Utiliza *Range* otimizado. |
| `for x in range(a, b, step)` | `for x in stride(...)` | Utiliza a função `stride` para passos diferentes de 1. |
| `for item in lista` | `for item in lista` | Loop de iteração padrão. |

### 3. Otimizações Idiomáticas

O Transpilador inclui uma regra de transformação para melhorar o código Swift gerado, substituindo operações Python complexas por métodos Swift otimizados:

| Padrão Python (para *Bubble Sort*) | Código Swift Gerado |
| :--- | :--- |
| `array[i], array[j] = array[j], array[i]` | `array.swapAt(i, j)` |

### 4. Funções e Métodos

* **Funções:** `def func(...)` é traduzido para `func func(...)`.
* **Construtores:** Mapeamento de `def __init__(self, ...)` para o construtor Swift **`init(...)`**.
* **F-strings:** Tradução de `f"Olá {nome}"` para a interpolação Swift `"Olá \(nome)"`.

## ⚙️ Arquitetura do Projeto

O transpilador é composto por três módulos de análise principais:

1.  **`SymbolTable`**: Gerencia escopos e mutabilidade, permitindo a correta emissão de `var` e `let`.
2.  **`TypeInferencer`**: Realiza uma análise de múltiplos passes na AST para inferir tipos de variáveis e retornos de função, essencial para a tipagem estática do Swift.
3.  **`PyToSwiftTranspiler`**: A classe principal que percorre a AST (`ast.NodeVisitor`) e gera o código Swift, garantindo a indentação correta em todos os blocos (`{ }`).
