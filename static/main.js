// ===== 1. SETUP INICIAL E SELEÇÃO DE ELEMENTOS =====
// O script começa "capturando" os elementos HTML com os quais irá interagir.
// Usar 'const' é uma boa prática para variáveis que não serão reatribuídas.

// Pega o elemento <canvas> e seu "contexto de desenho 2D", que é a API que o Chart.js usa para desenhar.
const perfCtx = document.getElementById('perfChart').getContext('2d');

// Seleciona os elementos <h2> onde os números de CPU e Memória serão exibidos.
const cpuEl = document.getElementById('cpu');
const memEl = document.getElementById('mem');

// Seleciona o <div> que servirá como container para a lista de serviços.
const servicesEl = document.getElementById('services');

// Seleciona os elementos do formulário para adicionar e remover serviços.
const addBtn = document.getElementById('addBtn');
const refreshBtn = document.getElementById('refreshBtn');
const nameInput = document.getElementById('name');
const urlInput = document.getElementById('url');

// ===== 2. INICIALIZAÇÃO DO GRÁFICO (CHART.JS) =====
// Arrays que guardarão os dados do gráfico. Serão preenchidos dinamicamente.
const labels = [];   // Rótulos do eixo X (tempo)
const cpuData = [];  // Dados da linha de CPU
const memData = [];  // Dados da linha de Memória

// Cria uma nova instância do gráfico, passando o contexto do canvas e a configuração.
const chart = new Chart(perfCtx, {
  type: 'line', // tipo de gráfico: linha
  data: {
    labels,     // array de rótulos (tempo)
    datasets: [
      { label: 'CPU %', data: cpuData, tension: 0.3 },    // primeira série (CPU)
      { label: 'Memória %', data: memData, tension: 0.3 } // segunda série (Memória)
    ]
  },
  options: {
    // Opções para customizar a aparência e o comportamento do gráfico.
    animation: false,  // Desativa a animação para que as atualizações sejam instantâneas.
    responsive: true,  // Permite que o gráfico se redimensione com a janela do navegador.
    scales: {
      y: { beginAtZero: true, suggestedMax: 100 } // Força o eixo Y a começar em 0 e sugere 100 como máximo.
    },
    plugins: {
      legend: { labels: { color: '#e6e9f2' } } // Muda a cor do texto da legenda para combinar com o tema escuro.
    }
  }
});

// ===== 3. FUNÇÕES AUXILIARES E DE LÓGICA =====

// Função que gera o HTML para uma "badge" de status (up, degraded, down).
function badge(status) {
  // Mapeia o status recebido da API para uma classe CSS correspondente.
  const cls = status === 'up' ? 'up' : status === 'degraded' ? 'degraded' : 'down';
  // Retorna uma string HTML. Template literals (com `) facilitam a interpolação.
  return `<span class="badge ${cls}">${status}</span>`;
}

// Função "wrapper" para a API fetch, simplificando requisições e tratamento de erros.
// Usar 'async' permite o uso de 'await' dentro da função.
async function fetchJSON(url, opts={}) {
  const res = await fetch(url, opts);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// Busca métricas de CPU/Memória do backend e atualiza a UI
// Esta é uma função assíncrona, pois depende de uma chamada de rede.
async function loadMetrics() {
  try {
    // 'await' pausa a função até que a requisição para /metrics seja concluída.
    const data = await fetchJSON('/metrics');

    // Atualiza os KPIs de CPU e Memória no HTML
    cpuEl.textContent = `${data.cpu.toFixed(0)}%`;
    memEl.textContent = `${data.memory.toFixed(0)}%`;

    // Adiciona ponto ao gráfico
    const time = new Date(data.timestamp * 1000).toLocaleTimeString(); // Converte timestamp UNIX para hora local.
    labels.push(time);
    cpuData.push(data.cpu);
    memData.push(data.memory);

    // Mantém apenas os últimos 30 pontos (para não crescer infinito)
    if (labels.length > 30) {
      labels.shift();
      cpuData.shift();
      memData.shift();
    }

    // Redesenha o gráfico com os novos dados. 'none' evita a animação.
    chart.update('none');
  } catch (e) {
    // Em caso de falha (ex: rede offline), simplesmente não atualizamos os KPIs.
    // O console do navegador ainda mostrará o erro de 'fetchJSON'.
  }
}

// Busca lista de serviços e desenha no HTML
async function loadServices() {
  try {
    // Busca a lista de serviços já com status e latência do backend.
    const list = await fetchJSON('/services');

    // Monta HTML de cada serviço como um "card" pequeno
    servicesEl.innerHTML = `
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;">
        ${list.map(s => `
          <div class="card" style="padding:12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <strong title="${s.url}">${s.name}</strong> <!-- 'title' cria um tooltip com a URL completa -->
              ${badge(s.status)} <!-- badge colorida de status -->
            </div>
            <!-- O operador '??' (nullish coalescing) mostra '-' se a latência for null ou undefined. -->
            <div class="muted">latência: ${s.latency_ms ?? '-'} ms</div> 
            <div class="muted" style="margin-top:6px;font-size:12px;word-break:break-all;">${s.url}</div>
            <!-- O 'onclick' chama uma função global. A substituição de aspas é uma segurança. -->
            <button style="margin-top:8px;" onclick="removeService('${s.name.replace(/'/g, "\\'")}')">Remover</button>
          </div>
        `).join('')}
      </div>
    `;
  } catch (e) {
    // Se a API falhar, mostra erro na UI
    servicesEl.innerHTML = `<span class="badge down">erro</span> Falha ao consultar /services`;
  }
}

// Adiciona novo serviço via POST /config
// Esta função é chamada quando o botão "Adicionar" é clicado.
async function addService() {
  const name = nameInput.value.trim();
  const url = urlInput.value.trim();
  if (!name || !url) {
    alert('Preencha nome e URL.');
    return;
  }
  try {
    // Envia os dados para a API /config usando o método POST.
    await fetchJSON('/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, type: 'http', url })
    });
    // Limpa os campos após adicionar
    nameInput.value = '';
    urlInput.value = '';
    // Recarrega a lista
    await loadServices();
  } catch (e) {
    alert('Falha ao adicionar serviço. Verifique se o nome já existe e a URL é válida.');
  }
}

// Remove serviço via DELETE /config
// Esta função é chamada pelo 'onclick' do botão "Remover" de cada serviço.
async function removeService(name) {
  if (!confirm(`Remover serviço "${name}"?`)) return;
  try {
    // Envia o nome do serviço a ser removido para a API /config via DELETE.
    await fetchJSON('/config', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    await loadServices();
  } catch (e) {
    alert('Falha ao remover serviço.');
  }
}

// ===== 4. EVENT LISTENERS E INICIALIZAÇÃO =====

// Para que o `onclick="removeService(...)"` no HTML funcione, a função precisa estar no escopo global (window).
window.removeService = removeService;

// Adiciona "escutadores de eventos" aos botões. Esta é a forma moderna de lidar com interações do usuário.
addBtn.addEventListener('click', addService);
refreshBtn.addEventListener('click', loadServices);

// Chama as funções uma vez no início para popular a tela imediatamente, sem esperar o primeiro intervalo.
loadMetrics();
loadServices();

// Configura o "polling": executa as funções de atualização em intervalos regulares.
// `setInterval` executa uma função repetidamente a cada X milissegundos.
setInterval(loadMetrics, 3000);
setInterval(loadServices, 5000);
