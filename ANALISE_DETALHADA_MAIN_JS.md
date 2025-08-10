# Análise Detalhada do `main.js` - Um Curso Prático

Este documento é um guia de estudo para o arquivo `static/main.js`. Este script é o "cérebro" da nossa interface, responsável por toda a interatividade: buscar dados do servidor, atualizar os gráficos, renderizar a lista de serviços e lidar com as ações do usuário.

---

## 1. Setup Inicial: Conectando JavaScript ao HTML

A primeira parte do script é "capturar" os elementos HTML com os quais vamos interagir. Fazemos isso usando seus IDs.

```javascript
// Seleciona o contexto 2D do <canvas id="perfChart"> para o Chart.js desenhar
const perfCtx = document.getElementById('perfChart').getContext('2d');

// Seleciona elementos HTML pelo ID para atualizar KPIs de CPU e Memória
const cpuEl = document.getElementById('cpu');
const memEl = document.getElementById('mem');

// Container onde serão desenhados os cards dos serviços
const servicesEl = document.getElementById('services');

// Seleciona botões e campos de input do formulário "Adicionar Serviço"
const addBtn = document.getElementById('addBtn');
// ... e outros inputs
```

### Conceitos de JavaScript:

*   `const`: Declara uma variável cujo valor não pode ser reatribuído. É uma boa prática usar `const` por padrão para evitar modificações acidentais.
*   `document.getElementById('id-do-elemento')`: Esta é uma das funções mais fundamentais do JavaScript para interagir com o HTML. Ela busca na página (o `document`) por um elemento que tenha o `id` especificado e retorna um objeto que o representa. Uma vez que temos esse objeto (ex: `cpuEl`), podemos manipular seu conteúdo, estilo, etc.
*   `.getContext('2d')`: Específico da tag `<canvas>`. Ele nos dá acesso à API de desenho 2D, que é o que a biblioteca Chart.js usará para renderizar o gráfico.

---

## 2. Inicialização do Gráfico (Chart.js)

Com o "contexto" do canvas em mãos, podemos criar e configurar nosso gráfico.

```javascript
const chart = new Chart(perfCtx, {
  type: 'line',
  data: {
    labels: [], // Começa vazio, será preenchido dinamicamente
    datasets: [
      { label: 'CPU %', data: [], tension: 0.3 },
      { label: 'Memória %', data: [], tension: 0.3 }
    ]
  },
  options: {
    animation: false,
    // ... outras opções
  }
});
```

### O que cada parte faz?

*   `new Chart(...)`: Cria uma nova instância de um gráfico da biblioteca Chart.js.
*   `type: 'line'`: Especifica que queremos um gráfico de linhas.
*   `data`: Um objeto que contém os dados a serem exibidos.
    *   `labels`: Um array de strings para os rótulos do eixo X (no nosso caso, os horários).
    *   `datasets`: Um array de objetos, onde cada objeto representa uma linha no gráfico (CPU e Memória). `data` dentro de cada dataset é o array de valores para o eixo Y.
*   `options`: Um objeto para customizar a aparência e o comportamento do gráfico.
    *   `animation: false`: Desativamos a animação padrão. Como atualizamos o gráfico a cada poucos segundos, a animação seria distrativa e consumiria recursos.
    *   `scales: { y: { beginAtZero: true, suggestedMax: 100 } }`: Garante que o eixo Y sempre comece em 0 e vá até (pelo menos) 100, o que faz sentido para porcentagens.

---

## 3. Comunicação com a API: `async/await` e `fetch`

O coração da interatividade é buscar dados do nosso backend Flask. Usamos a API `fetch` do navegador com a sintaxe `async/await` para tornar o código mais legível.

```javascript
async function fetchJSON(url, opts={}) {
  const res = await fetch(url, opts);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function loadMetrics() {
  try {
    const data = await fetchJSON('/metrics');
    // ... usa os dados
  } catch (e) {
    // ... trata o erro
  }
}
```

### Conceitos de JavaScript Assíncrono:

*   `async function`: Declara uma função como **assíncrona**. Isso significa que a função pode "pausar" sua execução sem bloquear o resto da página, o que é essencial para operações de rede (que podem demorar).
*   `await`: Só pode ser usado dentro de uma `async function`. Ele "pausa" a execução da função até que a `Promise` (a operação assíncrona, como o `fetch`) seja resolvida.
*   `fetch(url)`: A API moderna do navegador para fazer requisições de rede. Ela retorna uma `Promise` que, quando resolvida, nos dá um objeto de resposta.
*   `res.json()`: Um método do objeto de resposta que também retorna uma `Promise`. Ele lê o corpo da resposta e o converte de JSON para um objeto JavaScript.
*   `try...catch`: O bloco `try...catch` é a maneira padrão de lidar com erros em código síncrono e assíncrono com `async/await`. Se qualquer `await` falhar (a rede cair, o servidor retornar um erro 500), a execução pula para o bloco `catch`.

---

## 4. Manipulação do DOM: Atualizando a Página

Depois de buscar os dados, precisamos atualizar o que o usuário vê. Isso é chamado de **Manipulação do DOM** (Document Object Model).

```javascript
// Em loadMetrics()
cpuEl.textContent = `${data.cpu.toFixed(0)}%`;
memEl.textContent = `${data.memory.toFixed(0)}%`;
chart.update('none');

// Em loadServices()
servicesEl.innerHTML = `... HTML gerado dinamicamente ...`;
```

### O que cada linha faz?

*   `elemento.textContent = 'novo texto'`: A maneira mais segura e eficiente de alterar apenas o texto dentro de um elemento, sem interpretar nenhuma tag HTML.
*   `elemento.innerHTML = '...'`: Permite definir o conteúdo HTML completo de um elemento. É poderoso, mas deve ser usado com cuidado. Aqui, é perfeito para renderizar nossa lista de cards de serviço, que é uma estrutura HTML complexa.
*   `chart.update('none')`: Um método do Chart.js para redesenhar o gráfico com os novos dados que adicionamos aos arrays (`cpuData`, `memData`). O argumento `'none'` especifica que queremos uma atualização instantânea, sem animação.

---

## 5. Lidando com Ações do Usuário

O script também precisa responder a cliques em botões.

### Adicionar e Remover Serviços

```javascript
async function addService() {
  // 1. Pega os valores dos inputs
  const name = nameInput.value.trim();
  // 2. Faz a requisição POST para a API /config
  await fetchJSON('/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, type: 'http', url })
  });
  // 3. Limpa os inputs e recarrega a lista
  await loadServices();
}

async function removeService(name) {
  // 1. Pede confirmação ao usuário
  if (!confirm(`...`)) return;
  // 2. Faz a requisição DELETE para a API /config
  await fetchJSON('/config', { method: 'DELETE', ... });
  // 3. Recarrega a lista
  await loadServices();
}
```

### `onclick` e `addEventListener`

Existem duas maneiras de conectar uma função a um clique no nosso código:

1.  **`onclick` no HTML**:
    ```html
    <button onclick="removeService('Service Name')">Remover</button>
    ```
    Para que isso funcione, a função `removeService` precisa estar no **escopo global**. É por isso que temos a linha `window.removeService = removeService;`. É uma abordagem simples, mas menos flexível.

2.  **`addEventListener` no JavaScript**:
    ```javascript
    addBtn.addEventListener('click', addService);
    ```
    Esta é a abordagem moderna e preferida. Ela nos permite "escutar" por um evento (`'click'`) em um elemento (`addBtn`) e executar uma função (`addService`) quando ele ocorrer. Isso mantém a lógica de comportamento separada da estrutura HTML.

---

## 6. Atualizações Periódicas (`setInterval`)

A mágica do dashboard "em tempo real" (na verdade, polling) acontece aqui.

```javascript
setInterval(loadMetrics, 3000);
setInterval(loadServices, 5000);
```

*   `setInterval(funcao, milissegundos)`: Uma função do navegador que executa a `funcao` repetidamente, com um intervalo de `milissegundos` entre cada execução.
*   Aqui, estamos dizendo ao navegador para executar `loadMetrics` a cada 3000ms (3 segundos) e `loadServices` a cada 5000ms (5 segundos). Isso cria o efeito de atualização contínua do dashboard.

---

Este script é um excelente exemplo de como o JavaScript moderno funciona em uma aplicação de página única (SPA - Single Page Application) simples: ele inicializa a UI, busca dados de uma API de forma assíncrona, atualiza o DOM com os novos dados e responde a eventos do usuário, tudo sem a necessidade de recarregar a página inteira.