#!/bin/sh
# Read-only module presence report. Loaded modules do not prove offload traffic hits.
set -u
modules='qca_nss_dp qca_ssdk ecm qca_nss_ecm qca_ppe nft_flow_offload qca_nss_bridge_mgr qca_nss_vlan qca_nss_pppoe'
first=1
printf '{"ok":true,"semantics":"module-presence-only","modules":['
for m in $modules; do
  [ "$first" -eq 1 ] || printf ','
  first=0
  if [ -d "/sys/module/$m" ]; then loaded=true; else loaded=false; fi
  printf '{"name":"%s","loaded":%s}' "$m" "$loaded"
done
printf ']}\n'
