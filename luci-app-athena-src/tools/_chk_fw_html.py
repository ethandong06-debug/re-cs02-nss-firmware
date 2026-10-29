import paramiko
c=paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('127.0.0.1',2222,'vboxuser','vboxuser',timeout=15)
p='/home/vboxuser/jdc-build/immortalwrt_ipq-main/build_dir/target-aarch64_cortex-a53_musl/linux-qualcommax_ipq60xx/target-dir-c4e4fd53/www/luci-static/resources/view/athena/index.html'
cmds=[
 'grep -c "params:params" '+p,
 'grep -c "args.map" '+p,
 'ls -la '+p,
 'grep -o "AthenaWrt v1.2.[0-9]" '+p,
]
for cmd in cmds:
    i,o,e=c.exec_command(cmd,timeout=20)
    print('$ '+cmd)
    print(o.read().decode())
    err=e.read().decode().strip()
    if err: print('ERR:'+err)
c.close()
