#!/usr/bin/env bash
# capability_id: script.install-rainbond.ip-auto-detection
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
INSTALL_SCRIPTS=(
  "${REPO_ROOT}/script/install-rainbond.sh"
  "${REPO_ROOT}/script/install-rainbond-gpu.sh"
)
WINDOWS_INSTALL_SCRIPT="${REPO_ROOT}/script/install-rainbond.ps1"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

assert_contains() {
  local haystack=$1
  local needle=$2
  if ! grep -Fq -- "$needle" <<<"$haystack"; then
    fail "expected output to contain: ${needle}\noutput was:\n${haystack}"
  fi
}

assert_not_contains() {
  local haystack=$1
  local needle=$2
  if grep -Fq -- "$needle" <<<"$haystack"; then
    fail "expected output not to contain: ${needle}\noutput was:\n${haystack}"
  fi
}

assert_equals() {
  local actual=$1
  local expected=$2
  if [ "$actual" != "$expected" ]; then
    fail "expected '${expected}', got '${actual}'"
  fi
}

extract_verify_eip() {
  local script=$1
  extract_ip_functions "$script"
}

extract_function() {
  local script=$1
  local function_name=$2
  awk -v function_name="$function_name" '
    $0 == "function " function_name "() {" { capture = 1 }
    capture { print }
    /^}$/ && capture { capture = 0 }
  ' "$script"
}

extract_ip_functions() {
  local script=$1
  extract_language_helper "$script"
  extract_function "$script" rainbond_is_usable_ipv4
  extract_function "$script" verify_eip
  extract_function "$script" rainbond_is_private_ipv4
  extract_function "$script" rainbond_skip_ip_interface
  extract_function "$script" rainbond_candidate_host_ips
  extract_function "$script" rainbond_detect_host_eip
}

extract_language_helper() {
  local script=$1
  awk '
    /^function rainbond_use_chinese_prompt\(\) \{/ { capture = 1 }
    capture { print }
    /^}$/ && capture { capture = 0 }
  ' "$script"
}

write_stub() {
  local bin_dir=$1
  local name=$2
  local body=$3
  {
    printf '%s\n' '#!/usr/bin/env bash'
    printf '%s\n' "$body"
  } >"${bin_dir}/${name}"
  chmod +x "${bin_dir}/${name}"
}

run_language_case() {
  local script=$1
  local lang=$2
  local install_lang=$3
  local functions_file
  functions_file=$(mktemp)
  extract_language_helper "$script" >"$functions_file"

  LANG="$lang" RAINBOND_INSTALL_LANG="$install_lang" bash -c '
    set -e
    source "$1"
    if rainbond_use_chinese_prompt; then
      printf "zh\n"
    else
      printf "en\n"
    fi
  ' bash "$functions_file"
}

run_verify_case() {
  local script=$1
  local value=$2
  local functions_file
  functions_file=$(mktemp)
  extract_verify_eip "$script" >"$functions_file"

  set +e
  LANG=zh_CN.UTF-8 bash -c '
    set -e
    source "$1"
    if verify_eip "$2"; then
      printf "%s\n" "${EIP:-}"
    else
      exit 42
    fi
  ' bash "$functions_file" "$value"
  local status=$?
  set -e
  return "$status"
}

run_detect_case() {
  local script=$1
  local ip_output=$2
  local tmp_dir bin_dir functions_file
  tmp_dir=$(mktemp -d)
  bin_dir="${tmp_dir}/bin"
  functions_file="${tmp_dir}/ip-functions.sh"
  mkdir -p "$bin_dir"
  extract_ip_functions "$script" >"$functions_file"

  write_stub "$bin_dir" ip "cat <<'EOF'
${ip_output}
EOF"
  write_stub "$bin_dir" ifconfig "exit 1"

  PATH="${bin_dir}:/usr/bin:/bin" bash -c '
    set -e
    source "$1"
    if rainbond_detect_host_eip; then
      printf "%s\n" "${EIP:-}"
    else
      exit 42
    fi
  ' bash "$functions_file"
}

for install_script in "${INSTALL_SCRIPTS[@]}"; do
  script_content=$(sed -n '1,$p' "$install_script")

  assert_contains "$script_content" "rainbond_detect_host_eip"
  assert_contains "$script_content" "自动检测到服务器 IP"
  assert_contains "$script_content" "云服务器请用公网 IP"
  assert_contains "$script_content" "Cloud server, use public IP"
  assert_not_contains "$script_content" '[[ $result =~'
  assert_not_contains "$script_content" "浏览器访问云服务器，通常要用公网 IP"
  assert_not_contains "$script_content" "如果上面是内网 IP，从自己电脑访问时通常打不开"
  assert_not_contains "$script_content" "请到云厂商控制台复制公网 IP"
  assert_not_contains "$script_content" "If the detected URL above is a private IP"
  assert_not_contains "$script_content" "Copy the public IP from your cloud console"
  assert_not_contains "$script_content" "检测到以下 IP"
  assert_not_contains "$script_content" "Detected IP addresses"
  assert_not_contains "$script_content" "请输入安装完成后的浏览器访问 IP"
  assert_not_contains "$script_content" "Enter the browser access IP after installation"
  assert_not_contains "$script_content" "read res"
  assert_not_contains "$script_content" "输入序号"
  assert_not_contains "$script_content" "enter the index"
  assert_not_contains "$script_content" "ip_list="
  assert_not_contains "$script_content" "rainbond_auto_select_eip"
  assert_not_contains "$script_content" "api.ipify.org"
  assert_not_contains "$script_content" "volcstack/latest"

  selected_language=$(run_language_case "$install_script" C.UTF-8 "")
  assert_equals "$selected_language" "zh"

  selected_language=$(run_language_case "$install_script" en_US.UTF-8 "")
  assert_equals "$selected_language" "zh"

  selected_language=$(run_language_case "$install_script" C.UTF-8 en)
  assert_equals "$selected_language" "en"

  detected=$(run_detect_case "$install_script" "2: eth0    inet 203.0.113.10/24 brd 203.0.113.255 scope global eth0
3: eth1    inet 172.16.0.16/20 brd 172.16.15.255 scope global eth1")
  assert_equals "$detected" "172.16.0.16"

  detected=$(run_detect_case "$install_script" "2: docker0    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0
3: eth0    inet 10.0.0.5/24 brd 10.0.0.255 scope global eth0")
  assert_equals "$detected" "10.0.0.5"

  selected=$(run_verify_case "$install_script" 203.0.113.8)
  assert_equals "$selected" "203.0.113.8"

  if run_verify_case "$install_script" 2 >/dev/null 2>&1; then
    fail "expected numeric index input to be rejected"
  fi

  if run_verify_case "$install_script" 127.0.0.1 >/dev/null 2>&1; then
    fail "expected 127.0.0.1 to be rejected"
  fi

  if run_verify_case "$install_script" 0.0.0.0 >/dev/null 2>&1; then
    fail "expected 0.0.0.0 to be rejected"
  fi
done

windows_script_content=$(sed -n '1,520p' "$WINDOWS_INSTALL_SCRIPT")
assert_contains "$windows_script_content" "Get-InstallEIP"
assert_contains "$windows_script_content" "自动检测到服务器 IP"
assert_contains "$windows_script_content" "云服务器请用公网 IP"
assert_contains "$windows_script_content" "Cloud server, use public IP"
assert_not_contains "$windows_script_content" "浏览器访问云服务器，通常要用公网 IP"
assert_not_contains "$windows_script_content" "如果上面是内网 IP，从自己电脑访问时通常打不开"
assert_not_contains "$windows_script_content" "请到云厂商控制台复制公网 IP"
assert_not_contains "$windows_script_content" "If the detected URL above is a private IP"
assert_not_contains "$windows_script_content" "Copy the public IP from your cloud console"
assert_not_contains "$windows_script_content" "检测到以下 IP"
assert_not_contains "$windows_script_content" "Detected IP addresses"
assert_not_contains "$windows_script_content" "请输入安装完成后的浏览器访问 IP"
assert_not_contains "$windows_script_content" "Enter the browser access IP after installation"

printf 'PASS: install_rainbond_ip_prompt_test\n'
