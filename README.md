# Dashboard de Monitoramento (Flask + Chart.js)

Projeto **didático** e **reproduzível** para monitorar **CPU, Memória** e **status de serviços HTTP** com atualização periódica.

> Meta: qualquer pessoa (mesmo sem experiência) conseguir rodar localmente e entender como foi feito.

---

## ✅ O que este projeto faz
- Mostra **CPU** e **Memória** da máquina local (via `psutil`)
- Faz **health-check HTTP** de serviços configurados (ex.: `/health`)
- UI com **gráfico** (Chart.js) e **lista de serviços** (status + latência)
- Permite **adicionar/remover** serviços pela interface
- Configuração persistida em `services.json`

---

## 🧰 Requisitos
- **Python 3.10+** instalado
- Acesso à internet (para testar URLs públicas, opcional)

---

## ⬇️ Como baixar os arquivos
Você pode clonar do GitHub (quando publicar) **ou** baixar o ZIP gerado por mim neste passo-a-passo.

---

## ▶️ Como rodar localmente

### 1) Crie e ative um ambiente virtual
**Windows (PowerShell):**
```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
```
**Linux/Mac:**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Instale as dependências
```bash
pip install flask psutil requests
```

### 3) Inicie o servidor
```bash
python app.py
```
Abra o navegador em **http://127.0.0.1:5000**.

> A rota `/health` retorna `{"status":"ok"}` para auto‑teste.

---

## 📁 Estrutura dos arquivos
```
monitoring-dashboard/
├─ app.py                # Backend Flask (API e páginas)
├─ services.json         # Configuração persistida dos serviços (criado ao rodar)
├─ templates/
│  └─ index.html         # UI (HTML/CSS básico + Chart.js)
└─ static/
   └─ main.js            # Lógica de front-end (fetch, render, gráfico)
```

---

## ⚙️ Configuração de serviços (services.json)
O arquivo `services.json` guarda uma lista de objetos como:
```json
[
  { "name": "Local Health", "type": "http", "url": "http://127.0.0.1:5000/health" },
  { "name": "HTTP OK (200)", "type": "http", "url": "https://httpstat.us/200" },
  { "name": "HTTP 503 (Down)", "type": "http", "url": "https://httpstat.us/503" }
]
```
Você pode **adicionar/remover** serviços pela **interface** (seção “Adicionar Serviço”).

---

## 🛣 Rotas principais
- `GET /` → página do dashboard
- `GET /metrics` → CPU e memória (JSON)
- `GET /services` → status HTTP dos serviços (JSON)
- `GET /config` → lista de serviços configurados
- `POST /config` → adiciona serviço `{ name, type: "http", url }`
- `DELETE /config` → remove serviço `{ name }`
- `GET /health` → health local do app

---

## 🧪 Testes manuais rápidos
- Veja a CPU/Memória variarem ao abrir apps pesados.
- Adicione `https://httpstat.us/200` (UP) e `https://httpstat.us/503` (DOWN).
- Reinicie o app e confirme que suas configurações persistem (services.json).

---

## 🧭 Próximos passos (roadmap)
- [ ] Trocar polling por **WebSocket** (tempo real de verdade)
- [ ] **Autenticação** (login) para proteger /config
- [ ] **Logs estruturados** (JSON) e export CSV
- [ ] **Dockerfile** + `docker-compose.yml`
- [ ] **Deploy** (Render/Railway) e adicionar link de demo ao README
- [ ] Testes automatizados (pytest) e **GitHub Actions**

---

## 👨‍💻 Como publicar no GitHub (resumo)
```bash
git init
git add .
git commit -m "feat: dashboard de monitoramento MVP (Flask + Chart.js)"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/monitoring-dashboard.git
git push -u origin main
```

Crie prints e adicione ao README para valor de portfólio.

---

## 📜 Licença
MIT. Sinta‑se livre para usar, adaptar e evoluir.