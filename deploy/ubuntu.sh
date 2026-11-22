#!/usr/bin/env bash
# Deckva AI — быстрый деплой на Ubuntu (venv + systemd)
# Usage:
#   ./deploy/ubuntu.sh setup          # venv + зависимости + .env
#   sudo ./deploy/ubuntu.sh install   # systemd unit + автозапуск
#   sudo ./deploy/ubuntu.sh uninstall
#   ./deploy/ubuntu.sh status|logs|restart

set -euo pipefail

SERVICE_NAME="deckva-ai"
PORT="${DECKVA_AI_PORT:-9000}"
HOST="${DECKVA_AI_HOST:-127.0.0.1}"

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
  ok "setup готов. Дальше: sudo $0 install"
}

write_unit() {
  local user="$1"
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
ExecStart=${VENV_DIR}/bin/uvicorn app.main:app --host ${HOST} --port ${PORT} --workers 1
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

  write_unit "$user"
  systemctl daemon-reload
  systemctl enable --now "$SERVICE_NAME"
  sleep 1
  systemctl --no-pager --full status "$SERVICE_NAME" || true

  if curl -fsS "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
    ok "Сервис жив: http://${HOST}:${PORT}/health"
  else
    echo "⚠️  health пока не отвечает — смотри: journalctl -u ${SERVICE_NAME} -n 50"
  fi
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
  curl -fsS "http://${HOST}:${PORT}/health" && echo || echo "health: недоступен"
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
Deckva AI — Ubuntu deploy

  ./deploy/ubuntu.sh setup              # venv + pip + .env
  sudo ./deploy/ubuntu.sh install       # systemd + enable + start
  sudo ./deploy/ubuntu.sh restart
  sudo ./deploy/ubuntu.sh uninstall
  ./deploy/ubuntu.sh status
  ./deploy/ubuntu.sh logs [N]

Переменные окружения (опционально):
  DECKVA_AI_HOST=127.0.0.1
  DECKVA_AI_PORT=9000
EOF
}

main() {
  local cmd="${1:-}"
  shift || true
  case "$cmd" in
    setup) cmd_setup ;;
    install) cmd_install ;;
    uninstall) cmd_uninstall ;;
    status) cmd_status ;;
    logs) cmd_logs "${1:-80}" ;;
    restart) cmd_restart ;;
    -h|--help|help|"") usage ;;
    *) die "Неизвестная команда: $cmd (help — ./deploy/ubuntu.sh)" ;;
  esac
}

main "$@"
