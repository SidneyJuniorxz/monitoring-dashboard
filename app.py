# Importa objetos do Flask:
# - Flask: cria a aplicação web
# - render_template: renderiza arquivos HTML dentro da pasta "templates"
# - jsonify: converte dict/list do Python para JSON de forma segura
# - request: acessa dados da requisição (corpo JSON, método, headers etc.)
from flask import Flask, render_template, jsonify, request

# psutil: biblioteca para consultar métricas do sistema (CPU, memória, disco)
import psutil
# time: utilidades de tempo (timestamp atual, medir duração, etc.)
import time
# json: ler/gravar arquivos JSON
import json
# os: manipular caminhos de arquivo, checar existência, descobrir pasta atual
import os
# requests: fazer chamadas HTTP (GET/POST...) para checar serviços externos
import requests

# Cria a instância do app Flask.
# O __name__ informa ao Flask onde este arquivo está, para resolver caminhos relativos (templates/static).
app = Flask(__name__)

# Monta o caminho ABSOLUTO do arquivo de configuração "services.json".
# os.path.dirname(__file__) = pasta onde está este app.py
# os.path.join(..., "services.json") = junta a pasta com o nome do arquivo
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "services.json")

# Lista de serviços padrão (seed inicial).
# É usada para criar o arquivo services.json na primeira execução
# e também como fallback se o arquivo corromper.
DEFAULT_SERVICES = [
    {"name": "Local Health", "type": "http", "url": "http://127.0.0.1:5000/health"},
    {"name": "HTTP OK (200)", "type": "http", "url": "https://httpstat.us/200"},
    {"name": "HTTP 503 (Down)", "type": "http", "url": "https://httpstat.us/503"}
]

def load_config():
    """Lê a configuração de services.json.

    Se o arquivo não existir, cria um com os serviços padrão.
    Se o JSON estiver corrompido, retorna os serviços padrão como fallback.
    """
    if not os.path.exists(CONFIG_PATH):
        # Cria o arquivo com os serviços padrão
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_SERVICES, f, ensure_ascii=False, indent=2)
        return DEFAULT_SERVICES
    # Se o arquivo existir, tenta abri-lo e carregar seu conteúdo JSON
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            # Se o JSON estiver corrompido, retorna o padrão para não quebrar o app
            return DEFAULT_SERVICES

def save_config(services):
    """Salva a lista de serviços no arquivo services.json."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(services, f, ensure_ascii=False, indent=2)

@app.route("/health")
def health():
    """Rota de health-check do próprio aplicativo.
    
    Útil para auto-teste e para o serviço padrão "Local Health".
    """
    return jsonify({"status": "ok"})

@app.route("/")
def index():
    """Rota raiz: entrega a página HTML do dashboard."""
    return render_template("index.html")

@app.route("/metrics")
def metrics():
    """Devolve métricas de CPU e Memória da máquina local em JSON."""
    # psutil.cpu_percent(interval=0.1): mede % de uso da CPU.
    # interval pequeno (0.1s) dá leitura "fresca" sem travar o app.
    cpu = psutil.cpu_percent(interval=0.1)
    # psutil.virtual_memory().percent: % de memória usada
    mem = psutil.virtual_memory().percent
    # Timestamp UNIX (segundos desde 1970) — útil para rótulo do gráfico no front
    ts = int(time.time())
    # Pacotamos os dados num dict e retornamos como JSON
    data = {"timestamp": ts, "cpu": cpu, "memory": mem}
    return jsonify(data)

def check_http(url: str, timeout=3):
    """Checa um endpoint HTTP e retorna seu status e latência.

    Args:
        url (str): A URL a ser checada.
        timeout (int): Timeout da requisição em segundos.
    Returns:
        tuple[str, int | None]: Uma tupla com o status ('up', 'degraded', 'down') e a latência em ms.
    """
    status = "down"       # status default se algo der errado
    latency_ms = None     # latência default (None = não medido)
    try:
        start = time.time()                  # marca o início (para medir latência)
        resp = requests.get(url, timeout=timeout)  # faz a requisição GET com timeout
        elapsed = (time.time() - start) * 1000.0    # calcula latência em milissegundos
        latency_ms = int(elapsed)
        # Classificação por códigos HTTP:
        # 2xx/3xx → consideramos "up"
        if 200 <= resp.status_code < 400:
            status = "up"
        # 4xx → "degraded" (cliente errou; frequentemente indica endpoint vivo,
        # mas algo de entrada está incorreto; aqui usamos como alerta)
        elif 400 <= resp.status_code < 500:
            status = "degraded"
        # 5xx e outros → "down" (erro do servidor ou algo mais grave)
        else:
            status = "down"
    except Exception:
        # Qualquer exceção (timeout, DNS, conexão) vira "down"
        status = "down"
    return status, latency_ms

@app.route("/services", methods=["GET"])
def services():
    """Retorna a lista de serviços com status e latência atualizados.
    
    Lê a configuração de `services.json`, checa cada serviço HTTP
    e retorna uma lista de resultados para a UI.
    """
    services = load_config()   # lê a configuração persistida
    results = []               # aqui vamos montar a resposta já pronta para a UI
    for s in services:
        if s.get("type") == "http":
            # Para tipo "http", chamamos check_http(url) e coletamos status/latência
            st, lat = check_http(s.get("url"))
            results.append({
                "name": s.get("name"),
                "type": s.get("type"),
                "url": s.get("url"),
                "status": st,
                "latency_ms": lat
            })
        else:
            # Tipos não suportados (no futuro poderíamos ter tcp, ping, etc.)
            results.append({
                "name": s.get("name"),
                "type": s.get("type"),
                "url": s.get("url"),
                "status": "unsupported",
                "latency_ms": None
            })
    # Devolve a lista agregada (cada serviço já com status/latência)
    return jsonify(results)

@app.route("/config", methods=["GET", "POST", "DELETE"])
def config():
    """
    GET: retorna a lista atual de serviços.
    POST: adiciona um novo serviço. JSON esperado: { "name": "...", "type": "http", "url": "http://..." }
    DELETE: remove pelo 'name'. JSON: { "name": "..." }
    """
    services = load_config()  # sempre parte do que está persistido

    if request.method == "GET":
        # Retorna a lista "crua" (sem checar status)
        return jsonify(services)

    if request.method == "POST":
        # Tenta ler o corpo JSON. force=True aceita mesmo se header faltar;
        # silent=True evita exceção e retorna None; "or {}" garante dict.
        data = request.get_json(force=True, silent=True) or {}
        # Normaliza os campos (strip espaços, lower no type)
        name = (data.get("name") or "").strip()
        typ = (data.get("type") or "").strip().lower()
        url = (data.get("url") or "").strip()

        # Validação mínima: precisa de name, type=http e url
        if not name or typ != "http" or not url:
            return jsonify({"error": "Informe name, type='http' e url válidos."}), 400

        # Não permite duplicar nome (case-insensitive)
        if any(s["name"].lower() == name.lower() for s in services):
            return jsonify({"error": "Já existe um serviço com esse nome."}), 400

        # Se passou, adiciona e salva
        services.append({"name": name, "type": typ, "url": url})
        save_config(services)
        return jsonify({"message": "Serviço adicionado.", "service": {"name": name, "type": typ, "url": url}}), 201

    if request.method == "DELETE":
        # Lê o JSON com o nome a remover
        data = request.get_json(force=True, silent=True) or {}
        name = (data.get("name") or "").strip().lower()
        if not name:
            return jsonify({"error": "Informe o 'name' para remover."}), 400

        # Cria uma nova lista, mantendo apenas os serviços cujo nome não corresponde (case-insensitive)
        new_services = [s for s in services if s["name"].lower() != name]

        # Se o tamanho da lista não mudou, o serviço não foi encontrado
        if len(new_services) == len(services):
            return jsonify({"error": "Serviço não encontrado."}), 404

        # Salva a nova lista (sem o removido)
        save_config(new_services)
        return jsonify({"message": "Serviço removido.", "name": data.get("name")})

# "Ponto de entrada" quando executamos `python app.py`.
# debug=True ativa recarregamento automático e logs de erro detalhados.
# host='0.0.0.0' (opcional) permite acessar de outras máquinas na rede local.
if __name__ == "__main__":
    # host='0.0.0.0' se quiser acessar de outra máquina da rede
    app.run(debug=True) 