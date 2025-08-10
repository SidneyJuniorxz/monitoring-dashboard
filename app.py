from flask import Flask, render_template, jsonify, request
import psutil
import time
import json
import os
import requests


from urllib.parse import urlparse
# === NOVO: Socket.IO ===
from flask_socketio import SocketIO, emit
from datetime import timedelta
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from dotenv import load_dotenv

load_dotenv()  # carrega .env



app = Flask(__name__)

# cors_allowed_origins="*" simplifica no dev local; em produção, restrinja
socketio = SocketIO(app, cors_allowed_origins="*")

app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET", "dev-secret")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(seconds=int(os.environ.get("JWT_EXPIRES", "86400")))
jwt = JWTManager(app)

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "services.json")

DEFAULT_SERVICES = [
    {"name": "Local Health", "type": "http", "url": "http://127.0.0.1:5000/health"},
    {"name": "HTTP OK (200)", "type": "http", "url": "https://httpstat.us/200"},
    {"name": "HTTP 503 (Down)", "type": "http", "url": "https://httpstat.us/503"}
]

def load_config():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_SERVICES, f, ensure_ascii=False, indent=2)
        return DEFAULT_SERVICES
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return DEFAULT_SERVICES

def save_config(services):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(services, f, ensure_ascii=False, indent=2)
        
@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json(force=True, silent=True) or {}
    user = (data.get("username") or "").strip()
    pwd  = (data.get("password") or "").strip()
    if user == ADMIN_USER and pwd == ADMIN_PASS:
        token = create_access_token(identity=user)
        return jsonify({"access_token": token})
    return jsonify({"error": "credenciais inválidas"}), 401
        

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/metrics")
def metrics_http():
    # Mantemos essa rota opcionalmente (útil p/ testes e retrocompatibilidade)
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory().percent
    ts = int(time.time())
    data = {"timestamp": ts, "cpu": cpu, "memory": mem}
    return jsonify(data)

def check_http(url: str, timeout=5):
    status = "down"
    latency_ms = None
    try:
        parsed = urlparse(url)

        # 🔒 Atalho: se estiver checando o próprio /health local, não faça HTTP
        if parsed.scheme in ("http", "https") \
           and parsed.path == "/health" \
           and parsed.hostname in ("127.0.0.1", "localhost") \
           and (parsed.port in (None, 5000)):
            return "up", 0

        start = time.time()
        # 🚫 Evita uso de proxy para essa chamada
        resp = requests.get(url, timeout=timeout, proxies={"http": None, "https": None})
        elapsed = (time.time() - start) * 1000.0
        latency_ms = int(elapsed)

        if 200 <= resp.status_code < 400:
            status = "up"
        elif 400 <= resp.status_code < 500:
            status = "degraded"
        else:
            status = "down"
    except Exception:
        status = "down"
    return status, latency_ms


def collect_services_snapshot():
    """Monta a lista de serviços com status/latência (mesmo formato da rota /services)."""
    services = load_config()
    results = []
    for s in services:
        if s.get("type") == "http":
            st, lat = check_http(s.get("url"))
            results.append({
                "name": s.get("name"),
                "type": s.get("type"),
                "url": s.get("url"),
                "status": st,
                "latency_ms": lat
            })
        else:
            results.append({
                "name": s.get("name"),
                "type": s.get("type"),
                "url": s.get("url"),
                "status": "unsupported",
                "latency_ms": None
            })
    return results

@app.route("/services", methods=["GET"])
def services_http():
    # Mantemos a rota GET para testes; o front WebSocket receberá por eventos
    return jsonify(collect_services_snapshot())

@app.route("/config", methods=["GET", "POST", "DELETE"])
def config():
    services = load_config()

    if request.method == "GET":
        return jsonify(services)

    # ✅ a linha que faltava: delega POST/DELETE para a função protegida
    return _config_write_methods(services)

@jwt_required()
def _config_write_methods(services):
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        name = (data.get("name") or "").strip()
        typ = (data.get("type") or "").strip().lower()
        url = (data.get("url") or "").strip()
        if not name or typ != "http" or not url:
            return jsonify({"error": "Informe name, type='http' e url válidos."}), 400
        if any(s["name"].lower() == name.lower() for s in services):
            return jsonify({"error": "Já existe um serviço com esse nome."}), 400
        services.append({"name": name, "type": typ, "url": url})
        save_config(services)
        socketio.emit("services", collect_services_snapshot())
        return jsonify({"message": "Serviço adicionado.", "service": {"name": name, "type": typ, "url": url}}), 201

    if request.method == "DELETE":
        data = request.get_json(force=True, silent=True) or {}
        name = (data.get("name") or "").strip().lower()
        if not name:
            return jsonify({"error": "Informe o 'name' para remover."}), 400
        new_services = [s for s in services if s["name"].lower() != name]
        if len(new_services) == len(services):
            return jsonify({"error": "Serviço não encontrado."}), 404
        save_config(new_services)
        socketio.emit("services", collect_services_snapshot())
        return jsonify({"message": "Serviço removido.", "name": data.get("name")})
    

# ============ WebSocket (Socket.IO) ============

# Envia um snapshot inicial quando o cliente conecta
@socketio.on("connect")
def ws_connect():
    # manda métricas e serviços iniciais
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory().percent
    ts = int(time.time())
    emit("metrics", {"timestamp": ts, "cpu": cpu, "memory": mem})
    emit("services", collect_services_snapshot())

# Permite ao cliente solicitar refresh manual da lista de serviços
@socketio.on("refresh_services")
def ws_refresh_services():
    emit("services", collect_services_snapshot(), broadcast=True)

# Tarefa em background para emitir métricas/serviços periodicamente
def background_broadcast():
    while True:
        # métricas frequentes
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory().percent
        ts = int(time.time())
        socketio.emit("metrics", {"timestamp": ts, "cpu": cpu, "memory": mem})

        # serviços com frequência menor
        socketio.emit("services", collect_services_snapshot())

        socketio.sleep(10)  # 10s para serviços (ajuste como preferir)


# Inicia a tarefa em background assim que o servidor sobe
@socketio.on("connect")
def start_background_on_first_connect():
    # Truque: registramos um atributo na app para não iniciar múltiplas vezes
    if not hasattr(app, "bg_started"):
        app.bg_started = True
        socketio.start_background_task(background_broadcast)

if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)

