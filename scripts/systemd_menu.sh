#!/usr/bin/env bash

set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_DIR="${ROOT_DIR}/deploy/systemd"
SYSTEMD_TARGET_DIR="/etc/systemd/system"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"

API_UNIT="dailywall-api.service"
CRAWL_SERVICE_UNIT="dailywall-crawl.service"
CRAWL_TIMER_UNIT="dailywall-crawl.timer"

UNIT_FILES=(
  "${API_UNIT}"
  "${CRAWL_SERVICE_UNIT}"
  "${CRAWL_TIMER_UNIT}"
)

if [[ "${EUID}" -eq 0 ]]; then
  SUDO=()
else
  SUDO=(sudo)
fi

pause() {
  printf "\n按 Enter 返回菜单..."
  read -r _
}

print_header() {
  clear
  printf "DailyWall systemd 管理菜单\n"
  printf "项目目录: %s\n" "${ROOT_DIR}"
  printf "管理单元: %s, %s, %s\n\n" \
    "${API_UNIT}" "${CRAWL_SERVICE_UNIT}" "${CRAWL_TIMER_UNIT}"
}

confirm() {
  local prompt="$1"
  local answer

  printf "%s [y/N]: " "${prompt}"
  read -r answer
  case "${answer}" in
    y|Y|yes|YES|是) return 0 ;;
    *) return 1 ;;
  esac
}

require_systemctl() {
  if ! command -v systemctl >/dev/null 2>&1; then
    printf "错误: 未找到 systemctl。此脚本需要 systemd 环境。\n" >&2
    return 1
  fi
}

require_unit_sources() {
  local unit

  for unit in "${UNIT_FILES[@]}"; do
    if [[ ! -f "${SYSTEMD_DIR}/${unit}" ]]; then
      printf "错误: 缺少 unit 文件: %s\n" "${SYSTEMD_DIR}/${unit}" >&2
      return 1
    fi
  done
}

install_units() {
  local unit

  require_unit_sources || return 1

  printf "正在安装 systemd unit 文件...\n"
  for unit in "${UNIT_FILES[@]}"; do
    "${SUDO[@]}" install -D -m 0644 \
      "${SYSTEMD_DIR}/${unit}" \
      "${SYSTEMD_TARGET_DIR}/${unit}" || return 1
    printf "已安装: %s\n" "${SYSTEMD_TARGET_DIR}/${unit}"
  done

  "${SUDO[@]}" systemctl daemon-reload || return 1
  printf "已重新加载 systemd daemon。\n"
}

enable_and_start() {
  "${SUDO[@]}" systemctl enable --now "${API_UNIT}" || return 1
  "${SUDO[@]}" systemctl enable --now "${CRAWL_TIMER_UNIT}" || return 1
  printf "已设置开机自启，并已启动 API 服务和爬取定时器。\n"
}

restart_api() {
  "${SUDO[@]}" systemctl restart "${API_UNIT}"
}

start_api() {
  "${SUDO[@]}" systemctl start "${API_UNIT}"
}

stop_api() {
  "${SUDO[@]}" systemctl stop "${API_UNIT}"
}

start_timer() {
  "${SUDO[@]}" systemctl start "${CRAWL_TIMER_UNIT}"
}

stop_timer() {
  "${SUDO[@]}" systemctl stop "${CRAWL_TIMER_UNIT}"
}

require_python_bin() {
  if [[ ! -x "${PYTHON_BIN}" ]]; then
    printf "错误: 未找到可执行 Python: %s\n" "${PYTHON_BIN}" >&2
    printf "请先在项目目录执行: uv sync --dev\n" >&2
    return 1
  fi
}

run_crawl_with_args() {
  require_python_bin || return 1
  cd "${ROOT_DIR}" || return 1
  "${PYTHON_BIN}" "${ROOT_DIR}/scripts/crawl.py" "$@"
}

run_crawl_scheduled_now() {
  printf "正在通过 %s 按当前定时窗口触发爬取...\n" "${CRAWL_SERVICE_UNIT}"
  printf "注意: 如果当前时间不在配置窗口内，本次运行会失败。\n"
  "${SUDO[@]}" systemctl start "${CRAWL_SERVICE_UNIT}" || return 1
  systemctl status "${CRAWL_SERVICE_UNIT}" --no-pager
}

run_crawl_all_markets() {
  printf "正在手动采集全部 MARKETS...\n"
  run_crawl_with_args
}

run_crawl_simulated_time() {
  local schedule_time

  printf "可用时间点: 00:10, 02:40, 06:10, 07:10, 11:10, 12:10, 15:10, 23:10\n"
  printf "请输入要模拟的时间点(HH:MM): "
  read -r schedule_time

  if [[ -z "${schedule_time}" ]]; then
    printf "已取消。\n"
    return 0
  fi

  printf "正在模拟 %s 时间点采集对应地区...\n" "${schedule_time}"
  run_crawl_with_args --scheduled-markets --schedule-time "${schedule_time}"
}

run_crawl_selected_markets() {
  local markets_text
  local market_args=()

  printf "请输入地区编码，支持空格或逗号分隔，例如: zh-CN en-US 或 zh-CN,en-US\n"
  printf "地区: "
  read -r markets_text

  if [[ -z "${markets_text}" ]]; then
    printf "已取消。\n"
    return 0
  fi

  read -r -a market_args <<< "${markets_text}"
  printf "正在采集指定地区: %s\n" "${markets_text}"
  run_crawl_with_args --markets "${market_args[@]}"
}

show_status() {
  printf "\n== %s ==\n" "${API_UNIT}"
  systemctl status "${API_UNIT}" --no-pager || true

  printf "\n== %s ==\n" "${CRAWL_TIMER_UNIT}"
  systemctl status "${CRAWL_TIMER_UNIT}" --no-pager || true

  printf "\n== 定时器 ==\n"
  systemctl list-timers "${CRAWL_TIMER_UNIT}" --no-pager || true
}

show_logs() {
  local choice

  printf "\n查看日志:\n"
  printf "1) API 服务日志\n"
  printf "2) 爬取服务日志\n"
  printf "3) 爬取定时器日志\n"
  printf "4) 本地 systemd 爬取辅助日志\n"
  printf "0) 返回\n"
  printf "请选择: "
  read -r choice

  case "${choice}" in
    1) journalctl -u "${API_UNIT}" -n 100 --no-pager ;;
    2) journalctl -u "${CRAWL_SERVICE_UNIT}" -n 100 --no-pager ;;
    3) journalctl -u "${CRAWL_TIMER_UNIT}" -n 100 --no-pager ;;
    4) tail -n 100 "${ROOT_DIR}/logs/systemd-crawl.log" ;;
    0) return 0 ;;
    *) printf "无效选项。\n" ;;
  esac
}

health_check() {
  if command -v curl >/dev/null 2>&1; then
    curl -fsS "http://127.0.0.1:8000/api/health"
    printf "\n"
  else
    printf "错误: 未找到 curl。可手动打开 http://127.0.0.1:8000/api/health\n" >&2
    return 1
  fi
}

disable_and_stop() {
  printf "此操作会停止 API 服务和爬取定时器，并取消开机自启。\n"
  confirm "是否继续？" || return 0

  "${SUDO[@]}" systemctl disable --now "${CRAWL_TIMER_UNIT}" || return 1
  "${SUDO[@]}" systemctl disable --now "${API_UNIT}" || return 1
  printf "已停止 API 服务和爬取定时器，并已取消开机自启。\n"
}

run_and_pause() {
  "$@"
  pause
}

check_unit_sources() {
  local unit
  local missing=0

  printf "检查 deploy/systemd unit 文件:\n"
  for unit in "${UNIT_FILES[@]}"; do
    if [[ -f "${SYSTEMD_DIR}/${unit}" ]]; then
      printf "OK: %s\n" "${SYSTEMD_DIR}/${unit}"
    else
      printf "缺失: %s\n" "${SYSTEMD_DIR}/${unit}"
      missing=1
    fi
  done

  return "${missing}"
}

daemon_reload() {
  "${SUDO[@]}" systemctl daemon-reload || return 1
  printf "已重新加载 systemd daemon。\n"
}

install_enable_and_start() {
  install_units || return 1
  enable_and_start
}

enable_api() {
  "${SUDO[@]}" systemctl enable "${API_UNIT}"
}

disable_api() {
  "${SUDO[@]}" systemctl disable "${API_UNIT}"
}

api_status() {
  systemctl status "${API_UNIT}" --no-pager || true
}

enable_timer() {
  "${SUDO[@]}" systemctl enable "${CRAWL_TIMER_UNIT}"
}

disable_timer() {
  "${SUDO[@]}" systemctl disable "${CRAWL_TIMER_UNIT}"
}

timer_status() {
  systemctl status "${CRAWL_TIMER_UNIT}" --no-pager || true
}

show_timer_list() {
  systemctl list-timers "${CRAWL_TIMER_UNIT}" --no-pager || true
}

crawl_status() {
  systemctl status "${CRAWL_SERVICE_UNIT}" --no-pager || true
}

show_all_status() {
  printf "\n== %s ==\n" "${API_UNIT}"
  api_status

  printf "\n== %s ==\n" "${CRAWL_TIMER_UNIT}"
  timer_status

  printf "\n== %s ==\n" "${CRAWL_SERVICE_UNIT}"
  crawl_status

  printf "\n== 定时器 ==\n"
  show_timer_list
}

show_enable_status() {
  local unit

  printf "开机自启状态:\n"
  for unit in "${API_UNIT}" "${CRAWL_TIMER_UNIT}"; do
    printf "%s: " "${unit}"
    systemctl is-enabled "${unit}" 2>/dev/null || true
  done
}

show_active_status() {
  local unit

  printf "运行状态:\n"
  for unit in "${API_UNIT}" "${CRAWL_TIMER_UNIT}" "${CRAWL_SERVICE_UNIT}"; do
    printf "%s: " "${unit}"
    systemctl is-active "${unit}" 2>/dev/null || true
  done
}

tail_file() {
  local file="$1"

  if [[ ! -f "${file}" ]]; then
    printf "日志文件不存在: %s\n" "${file}"
    return 1
  fi

  tail -n 100 "${file}"
}

port_check() {
  if command -v ss >/dev/null 2>&1; then
    ss -ltnp | grep ':8000' || printf "未发现 8000 端口监听。\n"
  elif command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:8000 -sTCP:LISTEN || printf "未发现 8000 端口监听。\n"
  else
    printf "未找到 ss 或 lsof，无法检查端口。\n"
    return 1
  fi
}

db_file_check() {
  local db_file="${ROOT_DIR}/data/dailywall.db"

  if [[ -f "${db_file}" ]]; then
    ls -lh "${db_file}"
  else
    printf "数据库文件不存在: %s\n" "${db_file}"
    return 1
  fi
}

full_health_check() {
  printf "== API 健康检查 ==\n"
  health_check || true

  printf "\n== 端口检查 ==\n"
  port_check || true

  printf "\n== 数据库文件检查 ==\n"
  db_file_check || true
}

install_menu() {
  local choice

  while true; do
    print_header
    printf "安装 / 更新\n"
    printf "1) 检查 unit 源文件\n"
    printf "2) 安装或更新 unit 文件\n"
    printf "3) 仅执行 systemctl daemon-reload\n"
    printf "4) 一键安装、设置开机自启并启动\n"
    printf "0) 返回主菜单\n"
    printf "\n请选择: "
    read -r choice

    printf "\n"
    case "${choice}" in
      1) run_and_pause check_unit_sources ;;
      2) run_and_pause install_units ;;
      3) run_and_pause daemon_reload ;;
      4) run_and_pause install_enable_and_start ;;
      0) return 0 ;;
      *) printf "无效选项。\n"; pause ;;
    esac
  done
}

api_menu() {
  local choice

  while true; do
    print_header
    printf "API 服务管理\n"
    printf "1) 启动 API 服务\n"
    printf "2) 停止 API 服务\n"
    printf "3) 重启 API 服务\n"
    printf "4) 设置 API 开机自启\n"
    printf "5) 取消 API 开机自启\n"
    printf "6) 查看 API 状态\n"
    printf "0) 返回主菜单\n"
    printf "\n请选择: "
    read -r choice

    printf "\n"
    case "${choice}" in
      1) run_and_pause start_api ;;
      2) run_and_pause stop_api ;;
      3) run_and_pause restart_api ;;
      4) run_and_pause enable_api ;;
      5) run_and_pause disable_api ;;
      6) run_and_pause api_status ;;
      0) return 0 ;;
      *) printf "无效选项。\n"; pause ;;
    esac
  done
}

timer_menu() {
  local choice

  while true; do
    print_header
    printf "爬取定时器管理\n"
    printf "1) 启动爬取定时器\n"
    printf "2) 停止爬取定时器\n"
    printf "3) 设置定时器开机自启\n"
    printf "4) 取消定时器开机自启\n"
    printf "5) 查看定时器状态\n"
    printf "6) 查看下一次触发时间\n"
    printf "0) 返回主菜单\n"
    printf "\n请选择: "
    read -r choice

    printf "\n"
    case "${choice}" in
      1) run_and_pause start_timer ;;
      2) run_and_pause stop_timer ;;
      3) run_and_pause enable_timer ;;
      4) run_and_pause disable_timer ;;
      5) run_and_pause timer_status ;;
      6) run_and_pause show_timer_list ;;
      0) return 0 ;;
      *) printf "无效选项。\n"; pause ;;
    esac
  done
}

crawl_menu() {
  local choice

  while true; do
    print_header
    printf "手动爬取\n"
    printf "1) 通过 systemd 按当前定时窗口运行\n"
    printf "2) 手动采集全部 MARKETS\n"
    printf "3) 手动模拟定时时间点采集\n"
    printf "4) 手动采集指定地区\n"
    printf "5) 查看 crawl service 状态\n"
    printf "6) 查看最近 crawl service 日志\n"
    printf "7) 查看本地 systemd-crawl.log\n"
    printf "0) 返回主菜单\n"
    printf "\n请选择: "
    read -r choice

    printf "\n"
    case "${choice}" in
      1) run_and_pause run_crawl_scheduled_now ;;
      2) run_and_pause run_crawl_all_markets ;;
      3) run_and_pause run_crawl_simulated_time ;;
      4) run_and_pause run_crawl_selected_markets ;;
      5) run_and_pause crawl_status ;;
      6) run_and_pause journalctl -u "${CRAWL_SERVICE_UNIT}" -n 100 --no-pager ;;
      7) run_and_pause tail_file "${ROOT_DIR}/logs/systemd-crawl.log" ;;
      0) return 0 ;;
      *) printf "无效选项。\n"; pause ;;
    esac
  done
}

status_menu() {
  local choice

  while true; do
    print_header
    printf "状态查看\n"
    printf "1) 查看全部状态\n"
    printf "2) 查看开机自启状态\n"
    printf "3) 查看运行状态\n"
    printf "4) 查看定时器列表\n"
    printf "0) 返回主菜单\n"
    printf "\n请选择: "
    read -r choice

    printf "\n"
    case "${choice}" in
      1) run_and_pause show_all_status ;;
      2) run_and_pause show_enable_status ;;
      3) run_and_pause show_active_status ;;
      4) run_and_pause show_timer_list ;;
      0) return 0 ;;
      *) printf "无效选项。\n"; pause ;;
    esac
  done
}

logs_menu() {
  local choice

  while true; do
    print_header
    printf "日志查看\n"
    printf "1) API journal 日志\n"
    printf "2) crawl service journal 日志\n"
    printf "3) crawl timer journal 日志\n"
    printf "4) logs/systemd-crawl.log\n"
    printf "5) logs/api.log\n"
    printf "6) logs/error.log\n"
    printf "0) 返回主菜单\n"
    printf "\n请选择: "
    read -r choice

    printf "\n"
    case "${choice}" in
      1) run_and_pause journalctl -u "${API_UNIT}" -n 100 --no-pager ;;
      2) run_and_pause journalctl -u "${CRAWL_SERVICE_UNIT}" -n 100 --no-pager ;;
      3) run_and_pause journalctl -u "${CRAWL_TIMER_UNIT}" -n 100 --no-pager ;;
      4) run_and_pause tail_file "${ROOT_DIR}/logs/systemd-crawl.log" ;;
      5) run_and_pause tail_file "${ROOT_DIR}/logs/api.log" ;;
      6) run_and_pause tail_file "${ROOT_DIR}/logs/error.log" ;;
      0) return 0 ;;
      *) printf "无效选项。\n"; pause ;;
    esac
  done
}

health_menu() {
  local choice

  while true; do
    print_header
    printf "健康检查\n"
    printf "1) API 健康检查\n"
    printf "2) 检查 8000 端口\n"
    printf "3) 检查数据库文件\n"
    printf "4) 执行完整健康检查\n"
    printf "0) 返回主菜单\n"
    printf "\n请选择: "
    read -r choice

    printf "\n"
    case "${choice}" in
      1) run_and_pause health_check ;;
      2) run_and_pause port_check ;;
      3) run_and_pause db_file_check ;;
      4) run_and_pause full_health_check ;;
      0) return 0 ;;
      *) printf "无效选项。\n"; pause ;;
    esac
  done
}

show_main_menu() {
  printf "1) 安装 / 更新\n"
  printf "2) API 服务管理\n"
  printf "3) 爬取定时器管理\n"
  printf "4) 手动爬取\n"
  printf "5) 状态查看\n"
  printf "6) 日志查看\n"
  printf "7) 健康检查\n"
  printf "8) 停用 / 取消自启\n"
  printf "0) 退出\n"
  printf "\n请选择: "
}

main() {
  local choice

  require_systemctl || exit 1

  while true; do
    print_header
    show_main_menu
    read -r choice

    printf "\n"
    case "${choice}" in
      1) install_menu ;;
      2) api_menu ;;
      3) timer_menu ;;
      4) crawl_menu ;;
      5) status_menu ;;
      6) logs_menu ;;
      7) health_menu ;;
      8) run_and_pause disable_and_stop ;;
      0) exit 0 ;;
      *) printf "无效选项。\n"; pause ;;
    esac
  done
}

main "$@"
