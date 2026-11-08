#!/bin/sh
# Read-only NSS/ECM/PPE diagnostics.
# Module presence and nss_diag metadata do NOT prove that live traffic is hitting hardware offload.
set -u

json_str() { sed 's/\\/\\\\/g; s/"/\\"/g' | tr -d '\r\n'; }
modules='qca_nss_dp qca_ssdk ecm qca_nss_ecm qca_ppe nft_flow_offload qca_nss_bridge_mgr qca_nss_vlan qca_nss_pppoe'
first=1
printf '{"ok":true,"semantics":"module-presence-only","diagnostic_available":'
if command -v nss_diag >/dev/null 2>&1; then
  printf 'true'
  diag=$(nss_diag 2>/dev/null || true)
  mode=$(printf '%s\n' "$diag" | sed -n 's/.*NSS MODE[[:space:]:=]*//Ip' | head -1 | json_str)
  freq=$(printf '%s\n' "$diag" | sed -n 's/.*NSS FREQ[[:space:]:=]*//Ip' | head -1 | json_str)
  firmware=$(printf '%s\n' "$diag" | sed -n 's/.*NSS FW[[:space:]:=]*//Ip' | head -1 | json_str)
else
  printf 'false'
  mode=''; freq=''; firmware=''
fi
printf ',"mode":"%s","frequency":"%s","firmware":"%s","flow_hit_status":"not-measured","modules":[' "$mode" "$freq" "$firmware"
for m in $modules; do
  [ "$first" -eq 1 ] || printf ','
  first=0
  if [ -d "/sys/module/$m" ]; then loaded=true; else loaded=false; fi
  printf '{"name":"%s","loaded":%s}' "$m" "$loaded"
done
printf ']}\n'
