#!/usr/bin/env bash
# Deckva AI — деплой на Ubuntu (venv + systemd), порт 9000
#
# Полный пайплайн (на VPS из каталога deckva_ai):
#   chmod +x deploy/ubuntu.sh
#   ./deploy/ubuntu.sh setup
#   nano .env   # OPENROUTER_API_KEY=sk-or-...
#   sudo DECKVA_AI_HOST=0.0.0.0 ./deploy/ubuntu.sh install
#   sudo ufw allow 9000/tcp   # если ufw включён
#   ./deploy/ubuntu.sh status
#
# Если уже установлен на 127.0.0.1 — открыть наружу:
#   sudo ./deploy/ubuntu.sh public

set -euo pipefail

SERVICE_NAME="deckva-ai"
PORT="${DECKVA_AI_PORT:-9000}"
HOST="${DECKVA_AI_HOST:-0.0.0.0}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$APP_DIR/.venv"
ENV_FILE="$APP_DIR/.env"
UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

die() { echo "❌ $*" >&2; exit 1; }
info() { echo "→ $*"; }
ok() { echo "✅ $*"; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Нужна команда: $1"
}

run_as_root() {
  [[ "$(id -u)" -eq 0 ]] || die "Запусти с sudo: sudo $0 $*"
}

detect_user() {
  if [[ -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
    echo "$SUDO_USER"
  else
    stat -c '%U' "$APP_DIR"
  fi
}

# curl всегда на loopback — даже если listen 0.0.0.0
health_url() {
  echo "http://127.0.0.1:${PORT}/health"
}

cmd_setup() {
  need_cmd python3
  need_cmd curl

  info "Каталог: $APP_DIR"
  info "Python: $(python3 --version 2>&1)"

  if [[ ! -d "$VENV_DIR" ]]; then
    info "Создаю venv..."
    python3 -m venv "$VENV_DIR"
  else
    info "venv уже есть"
  fi

  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  pip install --upgrade pip
  pip install -r "$APP_DIR/requirements.txt"

  if [[ ! -f "$ENV_FILE" ]]; then
    if [[ -f "$APP_DIR/.env.example" ]]; then
      cp "$APP_DIR/.env.example" "$ENV_FILE"
      info "Создан .env из .env.example — заполни OPENROUTER_API_KEY"
    else
      cat >"$ENV_FILE" <<'EOF'
OPENROUTER_API_KEY=sk-or-...
EOF
      info "Создан пустой .env — заполни OPENROUTER_API_KEY"
    fi
  else
    info ".env уже есть"
  fi

  chmod 600 "$ENV_FILE" 2>/dev/null || true
  ok "setup готов. Дальше: nano .env && sudo DECKVA_AI_HOST=0.0.0.0 $0 install"
}

write_unit() {
  local user="$1"
  local host="$2"
  cat >"$UNIT_PATH" <<EOF
[Unit]
Description=Deckva AI (CORA / OpenRouter)
After=network.target

[Service]
Type=simple
User=${user}
Group=${user}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${VENV_DIR}/bin/uvicorn app.main:app --host ${host} --port ${PORT} --workers 1
Restart=on-failure
RestartSec=5
KillSignal=SIGTERM
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF
}

cmd_install() {
  run_as_root install
  [[ -x "$VENV_DIR/bin/uvicorn" ]] || die "Сначала: ./deploy/ubuntu.sh setup"
  [[ -f "$ENV_FILE" ]] || die "Нет .env — сначала setup и заполни ключи"

  if ! grep -qE '^OPENROUTER_API_KEY=.+' "$ENV_FILE" || grep -qE '^OPENROUTER_API_KEY=(sk-or-\.\.\.|)$' "$ENV_FILE"; then
    echo "⚠️  В .env похоже нет реального OPENROUTER_API_KEY — сервис может не работать"
  fi

  local user
  user="$(detect_user)"
  info "User: $user | host=$HOST port=$PORT"

  write_unit "$user" "$HOST"
  systemctl daemon-reload
  systemctl enable --now "$SERVICE_NAME"
  systemctl restart "$SERVICE_NAME"
  sleep 1
  systemctl --no-pager --full status "$SERVICE_NAME" || true

  echo
  ss -tlnp | grep ":${PORT}" || echo "⚠️  порт ${PORT} не слушается"
  if curl -fsS "$(health_url)" >/dev/null 2>&1; then
    ok "Сервис жив: $(health_url)"
    ok "Снаружи: http://<IP_VPS>:${PORT}/health"
  else
    echo "⚠️  health пока не отвечает — смотри: journalctl -u ${SERVICE_NAME} -n 50"
  fi
}

# Уже стоит на 127.0.0.1 → открыть 0.0.0.0:9000
cmd_public() {
  run_as_root public
  [[ -f "$UNIT_PATH" ]] || die "Unit не найден. Сначала: sudo $0 install"

  info "Ставлю --host 0.0.0.0 в $UNIT_PATH"
  sed -i 's/--host 127\.0\.0\.1/--host 0.0.0.0/' "$UNIT_PATH"
  # на случай если уже 0.0.0.0 — ок; если другой host — принудительно
  if ! grep -qE '--host 0\.0\.0\.0' "$UNIT_PATH"; then
    sed -i -E "s|--host [^ ]+|--host 0.0.0.0|" "$UNIT_PATH"
  fi

  systemctl daemon-reload
  systemctl restart "$SERVICE_NAME"
  sleep 1

  systemctl --no-pager --full status "$SERVICE_NAME" || true
  echo
  ss -tlnp | grep ":${PORT}" || true
  curl -fsS "$(health_url)" && echo || echo "health: недоступен"
  ok "Слушает 0.0.0.0:${PORT} — с ПК: http://<IP>:${PORT}/health"
  echo "   Firewall: sudo ufw allow ${PORT}/tcp"
}

cmd_uninstall() {
  run_as_root uninstall
  systemctl disable --now "$SERVICE_NAME" 2>/dev/null || true
  rm -f "$UNIT_PATH"
  systemctl daemon-reload
  ok "systemd unit удалён (venv и .env на месте)"
}

cmd_status() {
  systemctl --no-pager --full status "$SERVICE_NAME" || true
  echo
  ss -tlnp | grep ":${PORT}" || echo "порт ${PORT}: не слушается"
  curl -fsS "$(health_url)" && echo || echo "health: недоступен"
}

cmd_logs() {
  journalctl -u "$SERVICE_NAME" -n "${1:-80}" -f
}

cmd_restart() {
  run_as_root restart
  systemctl restart "$SERVICE_NAME"
  systemctl --no-pager --full status "$SERVICE_NAME" || true
}

usage() {
  cat <<EOF
Deckva AI — Ubuntu deploy (порт ${PORT})

Полный пайплайн:
  cd ~/servers/deckva_ai          # свой путь
  chmod +x deploy/ubuntu.sh
  ./deploy/ubuntu.sh setup
  nano .env                       # OPENROUTER_API_KEY=...
  sudo DECKVA_AI_HOST=0.0.0.0 ./deploy/ubuntu.sh install
  sudo ufw allow 9000/tcp         # если ufw active
  curl -sS http://127.0.0.1:9000/health

Уже установлен, только открыть наружу:
  sudo ./deploy/ubuntu.sh public

Команды:
  ./deploy/ubuntu.sh setup
  sudo ./deploy/ubuntu.sh install
  sudo ./deploy/ubuntu.sh public
  sudo ./deploy/ubuntu.sh restart
  sudo ./deploy/ubuntu.sh uninstall
  ./deploy/ubuntu.sh status
  ./deploy/ubuntu.sh logs [N]

Env:
  DECKVA_AI_HOST=0.0.0.0   (default)
  DECKVA_AI_PORT=9000
EOF
}

main() {
  local cmd="${1:-}"
  shift || true
  case "$cmd" in
    setup) cmd_setup ;;
    install) cmd_install ;;
    public) cmd_public ;;
    uninstall) cmd_uninstall ;;
    status) cmd_status ;;
    logs) cmd_logs "${1:-80}" ;;
    restart) cmd_restart ;;
    -h|--help|help|"") usage ;;
    *) die "Неизвестная команда: $cmd (help — ./deploy/ubuntu.sh)" ;;
  esac
}

main "$@"
