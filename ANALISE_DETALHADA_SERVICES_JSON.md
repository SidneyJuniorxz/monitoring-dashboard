# Análise Detalhada do `services.json` - Um Curso Prático

Este documento explica o propósito e a estrutura do arquivo `services.json`. Diferente de arquivos de código, o formato JSON não suporta comentários, então esta análise externa é a forma correta de documentá-lo.

---

## 1. O que é JSON?

JSON (JavaScript Object Notation) é um formato de texto leve para troca de dados. Apesar do nome, ele é independente de linguagem e se tornou o padrão de fato para APIs web e arquivos de configuração por ser fácil de ler e escrever tanto para humanos quanto para máquinas.

Suas estruturas básicas são:
*   **Objetos**: Coleções de pares chave/valor, delimitados por chaves `{}`. Ex: `{ "nome": "Serviço A" }`.
*   **Arrays (Listas)**: Listas ordenadas de valores, delimitadas por colchetes `[]`. Ex: `[ 1, 2, 3 ]`.

---

## 2. A Estrutura do `services.json`

Nosso arquivo `services.json` é um **array de objetos**.

```json
[
  {
    "name": "Local Health",
    "type": "http",
    "url": "http://127.0.0.1:5000/health"
  },
  {
    "name": "Youtube",
    "type": "http",
    "url": "https://www.youtube.com/"
  }
]
```

### O que cada parte significa?

*   `[...]`: O arquivo inteiro é um array (uma lista), o que significa que ele pode conter zero, um ou múltiplos serviços.
*   `{...}`: Cada item dentro do array é um objeto que representa um único serviço a ser monitorado.

### Os Campos (Chaves) de Cada Serviço:

*   `"name"` (string): Um nome amigável e **único** para o serviço, que será exibido na interface. É o identificador que usamos para remover um serviço.
*   `"type"` (string): O tipo de monitoramento a ser realizado. Atualmente, o projeto só suporta `"http"`, mas a existência deste campo permite que o projeto seja expandido no futuro para outros tipos (como `"ping"`, `"tcp"`, etc.).
*   `"url"` (string): A URL completa que o backend (`app.py`) irá verificar para determinar o status e a latência do serviço.

---

## 3. O Papel do Arquivo no Projeto

Este arquivo é o **banco de dados** da nossa aplicação. Ele é responsável pela **persistência de dados**.

1.  **Leitura**: Quando o `app.py` inicia ou quando a rota `/services` é chamada, a função `load_config()` lê este arquivo para saber quais serviços monitorar.
2.  **Escrita**: Quando um usuário adiciona ou remove um serviço através da interface, o backend (`app.py`) chama a função `save_config()`, que **sobrescreve** o conteúdo deste arquivo com a nova lista de serviços.

Isso garante que, mesmo que você feche e reabra o servidor, os serviços que você configurou permanecerão salvos.

### Primeira Execução

Se você apagar o `services.json` e rodar o `app.py` novamente, a função `load_config()` irá detectar sua ausência e o recriará automaticamente usando a lista `DEFAULT_SERVICES` definida no código Python. Isso garante que a aplicação sempre tenha um estado inicial funcional.

---

Com este arquivo, a documentação didática do projeto está completa, cobrindo o backend, o frontend e a camada de dados!