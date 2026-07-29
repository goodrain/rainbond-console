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
  extract_function "$script" is_truthy
  extract_function "$script" rainbond_is_usable_ipv4
  extract_function "$script" verify_eip
  extract_function "$script" rainbond_is_private_ipv4
  extract_function "$script" rainbond_skip_ip_interface
  extract_function "$script" rainbond_candidate_host_ips
  extract_function "$script" rainbond_detect_host_eip
  extract_function "$script" rainbond_detect_host_eip_value
  extract_function "$script" rainbond_public_ip_probe_enabled
  extract_function "$script" rainbond_public_ip_sources
  extract_function "$script" rainbond_probe_public_ip
  extract_function "$script" rainbond_tty_available
  extract_function "$script" rainbond_warn_ip_drift
  extract_function "$script" rainbond_build_access_lines
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

write_curl_stub() {
  local bin_dir=$1
  cat >"${bin_dir}/curl" <<'STUB'
#!/usr/bin/env bash
url=${@: -1}
printf '%s\n' "$*" >>"$CURL_STUB_LOG"
while IFS='|' read -r pattern response; do
  [ -n "$pattern" ] || continue
  if [ "$pattern" = "$url" ]; then
    [ -n "$response" ] && printf '%s\n' "$response"
    exit 0
  fi
done <"$CURL_STUB_MAP"
exit 22
STUB
  chmod +x "${bin_dir}/curl"
}

# Runs rainbond_probe_public_ip against a stubbed curl.
# $2 is a "<url>|<response>" map, $3 is where the stub records its calls.
run_probe_case() {
  local script=$1 map_content=$2 call_log=$3
  local tmp_dir bin_dir functions_file
  tmp_dir=$(mktemp -d)
  bin_dir="${tmp_dir}/bin"
  functions_file="${tmp_dir}/ip-functions.sh"
  mkdir -p "$bin_dir"
  extract_ip_functions "$script" >"$functions_file"
  printf '%s\n' "$map_content" >"${tmp_dir}/map"
  : >"$call_log"
  write_curl_stub "$bin_dir"

  CURL_STUB_LOG="$call_log" CURL_STUB_MAP="${tmp_dir}/map" \
    PATH="${bin_dir}:/usr/bin:/bin" bash -c '
    source "$1"
    rainbond_probe_public_ip
  ' bash "$functions_file"
}

run_probe_enabled_case() {
  local script=$1 probe_value=$2
  local functions_file
  functions_file=$(mktemp)
  extract_ip_functions "$script" >"$functions_file"

  EIP_PROBE="$probe_value" bash -c '
    source "$1"
    if rainbond_public_ip_probe_enabled; then
      printf "enabled\n"
    else
      printf "disabled\n"
    fi
  ' bash "$functions_file"
}

run_access_lines_case() {
  local script=$1 eip=$2 lan_ip=$3 public_ip=$4
  local functions_file
  functions_file=$(mktemp)
  extract_ip_functions "$script" >"$functions_file"

  EIP="$eip" RAINBOND_LAN_IP="$lan_ip" RAINBOND_PUBLIC_IP="$public_ip" bash -c '
    source "$1"
    rainbond_build_access_lines
    printf "%s\n%s\n" "$RAINBOND_ACCESS_LINES_ZH" "$RAINBOND_ACCESS_LINES_EN"
  ' bash "$functions_file"
}

run_drift_case() {
  local script=$1 recorded_eip=$2 ip_output=$3 map_content=$4 probe_enabled=$5
  local tmp_dir bin_dir functions_file
  tmp_dir=$(mktemp -d)
  bin_dir="${tmp_dir}/bin"
  functions_file="${tmp_dir}/ip-functions.sh"
  mkdir -p "$bin_dir"
  extract_ip_functions "$script" >"$functions_file"
  printf '%s\n' "$map_content" >"${tmp_dir}/map"
  write_curl_stub "$bin_dir"
  write_stub "$bin_dir" ip "cat <<'EOF'
${ip_output}
EOF"
  write_stub "$bin_dir" ifconfig "exit 1"

  CURL_STUB_LOG="${tmp_dir}/log" CURL_STUB_MAP="${tmp_dir}/map" EIP_PROBE="$probe_enabled" \
    PATH="${bin_dir}:/usr/bin:/bin" bash -c '
    send_msg() { :; }
    send_warn() { printf "WARN: %s\n" "$1"; }
    source "$1"
    rainbond_warn_ip_drift "$2"
  ' bash "$functions_file" "$recorded_eip"
}

for install_script in "${INSTALL_SCRIPTS[@]}"; do
  script_content=$(sed -n '1,$p' "$install_script")

  assert_contains "$script_content" "rainbond_detect_host_eip"
  assert_contains "$script_content" "自动检测到服务器 IP"
  assert_contains "$script_content" "云服务器请用公网 IP"
  assert_contains "$script_content" "Cloud server, use public IP"
  # the public IP lookup must stay opt-out-able and never block the install
  assert_contains "$script_content" "EIP_PROBE:-true"
  assert_contains "$script_content" "--connect-timeout 1 --max-time 2"
  assert_contains "$script_content" "--connect-timeout 2 --max-time 3"
  # the prompt reaches the user even when the installer is run through a pipe
  assert_contains "$script_content" "read -r -t \"\${RAINBOND_EIP_CONFIRM_TIMEOUT}\" answer </dev/tty"
  # a changed host IP is reported before the user hits a dead console link
  assert_contains "$script_content" 'rainbond_warn_ip_drift "$get_eip"'
  # the security group hint runs before the install, not only after it
  assert_contains "$script_content" "rainbond_print_access_ports_notice"
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

  probe_log=$(mktemp)
  probed=$(run_probe_case "$install_script" \
    "http://100.100.100.200/latest/meta-data/eipv4|203.0.113.20" "$probe_log")
  assert_equals "$probed" "203.0.113.20"
  probe_calls=$(wc -l <"$probe_log" | tr -d ' ')
  assert_equals "$probe_calls" "1"
  assert_contains "$(cat "$probe_log")" "--connect-timeout 1 --max-time 2"

  probe_log=$(mktemp)
  probed=$(run_probe_case "$install_script" "http://100.100.100.200/latest/meta-data/eipv4|
http://ip.3322.net|198.51.100.7" "$probe_log")
  assert_equals "$probed" "198.51.100.7"

  # a metadata service answering with a private address is not a public IP
  probe_log=$(mktemp)
  probed=$(run_probe_case "$install_script" "http://169.254.169.254/latest/meta-data/public-ipv4|10.0.0.9
https://api.ip.sb/ip|198.51.100.8" "$probe_log")
  assert_equals "$probed" "198.51.100.8"

  # an HTML error page must never be mistaken for an address
  probe_log=$(mktemp)
  if run_probe_case "$install_script" "https://api.ip.sb/ip|<html>not an ip</html>" "$probe_log" >/dev/null 2>&1; then
    fail "expected non-IP probe responses to be rejected"
  fi

  probe_log=$(mktemp)
  if run_probe_case "$install_script" "" "$probe_log" >/dev/null 2>&1; then
    fail "expected probe to fail when no source answers"
  fi

  assert_equals "$(run_probe_enabled_case "$install_script" "")" "enabled"
  assert_equals "$(run_probe_enabled_case "$install_script" false)" "disabled"
  assert_equals "$(run_probe_enabled_case "$install_script" 0)" "disabled"

  # public IP adopted: the LAN address stays visible as the second address
  access_lines=$(run_access_lines_case "$install_script" 203.0.113.20 172.16.0.16 203.0.113.20)
  assert_contains "$access_lines" "http://203.0.113.20:7070"
  assert_contains "$access_lines" "http://172.16.0.16:7070"
  assert_not_contains "$access_lines" "<公网IP>"

  # LAN IP kept: the detected public address is still offered
  access_lines=$(run_access_lines_case "$install_script" 172.16.0.16 172.16.0.16 203.0.113.20)
  assert_contains "$access_lines" "http://172.16.0.16:7070"
  assert_contains "$access_lines" "http://203.0.113.20:7070"

  # no public IP found: fall back to the generic hint
  access_lines=$(run_access_lines_case "$install_script" 172.16.0.16 172.16.0.16 "")
  assert_contains "$access_lines" "http://172.16.0.16:7070"
  assert_contains "$access_lines" "云服务器请用公网 IP"
  assert_contains "$access_lines" "Cloud server, use public IP"

  # a public EIP without a probe result needs no private-IP hint
  access_lines=$(run_access_lines_case "$install_script" 203.0.113.20 172.16.0.16 "")
  assert_not_contains "$access_lines" "<公网IP>"

  host_ip_output="2: eth0    inet 172.16.0.16/20 brd 172.16.15.255 scope global eth0"

  drift_output=$(run_drift_case "$install_script" 172.16.0.16 "$host_ip_output" "" false)
  assert_not_contains "$drift_output" "WARN:"

  drift_output=$(run_drift_case "$install_script" 203.0.113.20 "$host_ip_output" \
    "http://100.100.100.200/latest/meta-data/eipv4|203.0.113.20" true)
  assert_not_contains "$drift_output" "WARN:"

  drift_output=$(run_drift_case "$install_script" 198.51.100.99 "$host_ip_output" "" false)
  assert_contains "$drift_output" "WARN:"
  assert_contains "$drift_output" "198.51.100.99"

  drift_output=$(run_drift_case "$install_script" "" "$host_ip_output" "" false)
  assert_not_contains "$drift_output" "WARN:"
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
