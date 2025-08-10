
const perfCtx = document.getElementById('perfChart').getContext('2d');
const cpuEl = document.getElementById('cpu');
const memEl = document.getElementById('mem');
const servicesEl = document.getElementById('services');

const addBtn = document.getElementById('addBtn');
const refreshBtn = document.getElementById('refreshBtn');
const nameInput = document.getElementById('name');
const urlInput = document.getElementById('url');


const labels = [];
const cpuData = [];
const memData = [];
const userInput = document.getElementById('user');
const passInput = document.getElementById('pass');
const loginBtn  = document.getElementById('loginBtn');
const logoutBtn = document.getElementById('logoutBtn');
const authState = document.getElementById('authState');

function setAuthState() {
  const token = localStorage.getItem('jwt');
  authState.textContent = token ? 'Logado' : 'Deslogado';
}
setAuthState();

async function login() {
  const username = (userInput.value || '').trim();
  const password = (passInput.value || '').trim();
  if (!username || !password) { alert('Informe usuário e senha'); return; }
  const res = await fetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  if (res.ok) {
    const { access_token } = await res.json();
    localStorage.setItem('jwt', access_token);
    setAuthState();
    alert('Login ok!');
  } else {
    alert('Credenciais inválidas');
  }
}

function logout() {
  localStorage.removeItem('jwt');
  setAuthState();
  alert('Saiu!');
}

loginBtn.addEventListener('click', login);
logoutBtn.addEventListener('click', logout);


const chart = new Chart(perfCtx, {
  type: 'line',
  data: {
    labels,
    datasets: [
      { label: 'CPU %', data: cpuData, tension: 0.3 },
      { label: 'Memória %', data: memData, tension: 0.3 },
    ]
  },
  options: {
    animation: false,
    responsive: true,
    scales: { y: { beginAtZero: true, suggestedMax: 100 } },
    plugins: { legend: { labels: { color: '#e6e9f2' } } }
  }
});

function badge(status) {
  const cls = status === 'up' ? 'up' : status === 'degraded' ? 'degraded' : 'down';
  return `<span class="badge ${cls}">${status}</span>`;
}

async function fetchJSON(url, opts={}) {
  const res = await fetch(url, opts);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// === WebSocket (Socket.IO) ===
const socket = io(); // mesma origem do Flask

socket.on('connect', () => {
  // opcional: console.log('socket conectado');
});

socket.on('metrics', (data) => {
  // Atualiza KPIs
  cpuEl.textContent = `${data.cpu.toFixed(0)}%`;
  memEl.textContent = `${data.memory.toFixed(0)}%`;

  // Atualiza série temporal
  const time = new Date(data.timestamp * 1000).toLocaleTimeString();
  labels.push(time);
  cpuData.push(data.cpu);
  memData.push(data.memory);
  if (labels.length > 30) { labels.shift(); cpuData.shift(); memData.shift(); }
  chart.update('none');
});

socket.on('services', (list) => {
  servicesEl.innerHTML = `
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;">
      ${list.map(s => `
        <div class="card" style="padding:12px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <strong title="${s.url}">${s.name}</strong>
            ${badge(s.status)}
          </div>
          <div class="muted">latência: ${s.latency_ms ?? '-'} ms</div>
          <div class="muted" style="margin-top:6px;font-size:12px;word-break:break-all;">${s.url}</div>
          <button style="margin-top:8px;" onclick="removeService('${s.name.replace(/'/g, "\\'")}')">Remover</button>
        </div>
      `).join('')}
    </div>
  `;
});

// === Ações via HTTP continuam iguais ===
async function addService() {
  const name = nameInput.value.trim();
  const url = urlInput.value.trim();
  if (!name || !url) { alert('Preencha nome e URL.'); return; }
  const token = localStorage.getItem('jwt');
  if (!token) { alert('Faça login para adicionar.'); return; }

  try {
    await fetchJSON('/config', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ name, type: 'http', url })
    });
    nameInput.value = ''; urlInput.value = '';
    socket.emit('refresh_services');
  } catch (e) {
    alert('Falha ao adicionar serviço (verifique login/token).');
  }
}

async function removeService(name) {
  if (!confirm(`Remover serviço "${name}"?`)) return;
  const token = localStorage.getItem('jwt');
  if (!token) { alert('Faça login para remover.'); return; }

  try {
    await fetchJSON('/config', {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ name })
    });
    socket.emit('refresh_services');
  } catch (e) {
    alert('Falha ao remover serviço (verifique login/token).');
  }
}


window.removeService = removeService;
addBtn.addEventListener('click', addService);
// o botão de "Atualizar Lista" pode pedir refresh via socket também:
refreshBtn.addEventListener('click', () => socket.emit('refresh_services'));
