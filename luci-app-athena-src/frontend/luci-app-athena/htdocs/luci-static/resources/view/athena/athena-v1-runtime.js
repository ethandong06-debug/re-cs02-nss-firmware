/* AthenaWrt V1.0 device-side interaction adapter.
 * Every privileged operation goes through /usr/libexec/athena-v1.sh.
 */
(function(){
'use strict';
const P=window.UbusProvider;
const V=window.AthenaV1={
 async call(action,args=[],timeout=45000){
  if(!P||P.mode!=='device'||!P.session)throw new Error('请先登录路由器');
  const argv=[String(action),...(args||[]).map(String)];
  if(argv.length>10||argv.some(x=>x.length>256||/[\u0000-\u001f]/.test(x)))throw new Error('参数超出安全范围');
  const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),timeout);
  try{
   const resp=await fetch('/ubus/',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},signal:ctrl.signal,
    body:JSON.stringify({jsonrpc:'2.0',id:Date.now(),method:'call',params:[P.session,'file','exec',{command:'/usr/libexec/athena-v1.sh',params:argv}]})});
   if(!resp.ok)throw new Error('RPC HTTP '+resp.status);
   const j=await resp.json(),env=j&&j.result;
   if(!Array.isArray(env)||env[0]!==0)throw new Error(env&&env[0]===6?'V1 网关 ACL 拒绝该操作':'后端 RPC 调用失败');
   const p=env[1]||{};if(Number(p.rc||0)!==0)throw new Error((p.stderr||'').trim()||'后端执行失败');
   const out=(p.stdout||'').trim();if(!out)return{ok:true};
   let data;try{data=JSON.parse(out);}catch(e){throw new Error('后端 JSON 格式无效');}
   if(data&&data.ok===false)throw new Error(data.msg||'后端拒绝该操作');return data;
  }catch(e){if(e&&e.name==='AbortError')throw new Error('路由器操作超时');throw e;}finally{clearTimeout(timer);}
 },
 async loadExtra(){
  if(!P||P.mode!=='device')return;
  const names=['parents','backups','logs','disks','wifiSchedule','rebootSchedule','backupSchedule','packages','availablePackages','apps','services','blocked'];
  const jobs=[()=>V.call('parent-list'),()=>V.call('backup-list'),()=>V.call('logs-read',['all']),()=>V.call('disk-list'),
   ()=>V.call('wifi-schedule-status'),()=>V.call('reboot-status'),()=>V.call('backup-schedule-get'),()=>V.call('packages-installed'),
   ()=>V.call('packages-available'),()=>V.call('apps-list'),()=>V.call('services-list'),()=>V.call('clients-list')];
  const vals=await Promise.all(jobs.map(async f=>{try{return await f();}catch(e){return null;}})),d=Object.fromEntries(names.map((n,i)=>[n,vals[i]]));
  if(d.parents&&Array.isArray(d.parents.rules))P.state.parentalRules=d.parents.rules.map(r=>{
   const c=(P.state.clients||[]).find(x=>(x.mac||'').toLowerCase()===(r.mac||'').toLowerCase())||{};
   return{name:c.name||r.mac,mac:r.mac,ip:c.ip||'',timeStart:r.start||'—',timeEnd:r.end||'—',
    days:(r.days||[]).map(n=>['日','一','二','三','四','五','六'][Number(n)]).join('、'),status:'已配置'};
  });
  if(d.backups&&Array.isArray(d.backups.backups))P.state.backups=d.backups.backups.map(b=>({name:b.file,size:(Number(b.size_kb)||0)+' KB',date:b.file,type:'路由器配置备份'}));
  if(d.logs&&Array.isArray(d.logs.logs))P.state.logs=d.logs.logs;
  if(d.disks&&Array.isArray(d.disks.disks))P.state.disks=d.disks.disks;
  if(d.wifiSchedule)P.state.wifiSched=d.wifiSchedule;
  if(d.backupSchedule)P.state.backupSchedule=d.backupSchedule;
  if(d.packages&&Array.isArray(d.packages.packages)&&typeof opkgState!=='undefined')opkgState.installed=d.packages.packages.map(x=>({name:x.name,version:x.version||'—',size:x.size||'—',protected:!!x.protected}));
  if(d.availablePackages&&Array.isArray(d.availablePackages.packages)&&typeof opkgState!=='undefined')opkgState.available=d.availablePackages.packages;
  if(d.apps)P.state.activeApps=d.apps.apps||[];
  if(d.services)P.state.services=d.services.services||d.services;
  if(d.blocked&&Array.isArray(d.blocked.blocked)){const set=new Set(d.blocked.blocked.map(x=>String(x).toLowerCase()));(P.state.clients||[]).forEach(c=>{if(c.mac)c.status=set.has(c.mac.toLowerCase())?'已拉黑':(c.status==='已拉黑'?'在线':c.status);});}
  return d;
 },
 async refresh(){if(P&&P.mode==='device'){await P.pollOnce();await V.loadExtra();if(typeof renderPage==='function'&&typeof current!=='undefined')renderPage(current);}},
 async downloadBackup(file){
  const r=await V.call('backup-download',[file]);if(!r.base64)throw new Error('后端未返回备份内容');
  const bin=atob(r.base64),bytes=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)bytes[i]=bin.charCodeAt(i);
  const blob=new Blob([bytes],{type:'application/gzip'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=r.file||file;document.body.appendChild(a);a.click();setTimeout(()=>{a.remove();URL.revokeObjectURL(url);},500);
 },
 async restoreBackup(file){
  openModal('备份恢复暂不开放','<div class="sim-notice warning">为保护现网 PPPoE、VLAN 2044、IPv6、防火墙、OpenClash 和 NSS/ECM 配置，本版本不开放整份系统配置恢复。可创建和下载备份；恢复请通过原生 LuCI 先核对归档内容后操作。</div><div class="sim-modal-actions"><button class="sim-btn primary" onclick="closeModal()">知道了</button></div>');
 },
 async doRestore(){throw new Error('V1.0 页面不开放整份配置恢复');},
 async formatDisk(){const dev=document.getElementById('v1-format-dev')?.value,fs=document.getElementById('v1-format-fs')?.value,confirm=document.getElementById('v1-format-confirm')?.value;if(confirm!=='FORMAT'){toast('确认文本不匹配，未格式化');return;}try{const r=await V.call('disk-format',[dev,fs,'CONFIRM_FORMAT']);closeModal();await V.loadExtra();toast(r.msg||'格式化已完成');}catch(e){toast('格式化失败：'+e.message);}},
 async rebootNow(){try{await V.call('reboot-now',['CONFIRM_REBOOT']);closeModal();toast('路由器已接受重启命令');}catch(e){toast('重启失败：'+e.message);}},
 async removeNas(){try{const r=await V.call('nas-remove',['CONFIRM_REMOVE']);closeModal();await V.loadExtra();renderPage('NAS 文件共享');toast(r.msg||'NAS 已卸载');}catch(e){toast('NAS 卸载失败：'+e.message);}},
 async removePackage(name){try{const r=await V.call('packages-remove',[name]);closeModal();await V.loadExtra();renderPage('软件包管理');toast(r.msg||'软件包已卸载');}catch(e){toast('卸载失败：'+e.message);}}
};
const oldUnlock=window.unlockAthenaConsole;
window.unlockAthenaConsole=function(){oldUnlock();if(P&&P.mode==='device')V.loadExtra().then(()=>{if(typeof renderPage==='function'&&typeof current!=='undefined')renderPage(current);}).catch(console.warn);};
if(P&&typeof P.poll==='function'){const oldPoll=P.poll.bind(P);P.poll=async function(){await oldPoll();if(this.mode==='device')await V.loadExtra();};}

window.saveWifiModalConfig=async function(band){
 const id=({'2.4GHz':'b24','5.2GHz':'b52','5.8GHz':'b58'})[band],ssid=document.getElementById('wf-ssid')?.value||'',sec=document.getElementById('wf-security')?.value||'WPA2-PSK',chan=document.getElementById('wf-channel')?.value||'auto',width=document.getElementById('wf-width')?.value||'20MHz',pwd=document.getElementById('wf-pwd')?.value||'',hidden=document.getElementById('wf-hidden')?.checked?1:0,enabled=document.getElementById('wf-enable')?.checked!==false;
 try{await V.call('wifi-set',[id,ssid,pwd,chan,width,sec,hidden]);await V.call(enabled?'wifi-enable':'wifi-disable',[id]);closeModal();await V.refresh();toast(band+' 配置已由路由器确认；发射功率保持现有值');}catch(e){toast('无线配置失败：'+e.message);}
};
window.saveWifiSchedule=async function(){
 const off=document.getElementById('sched-off-time')?.value||'01:00',on=document.getElementById('sched-on-time')?.value||'06:30',b24=document.getElementById('sched-band-24')?.checked!==false?1:0,b52=document.getElementById('sched-band-52')?.checked!==false?1:0,b58=document.getElementById('sched-band-58')?.checked?1:0;
 try{const r=await V.call('wifi-schedule-set',[off,on,b24,b52,b58]);await V.loadExtra();toast(r.msg||'Wi-Fi 定时已保存；其他 crontab 项未修改');}catch(e){toast('Wi-Fi 定时保存失败：'+e.message);}
};
window.toggleClientBlacklist=async function(ip){const c=(P.state.clients||[]).find(x=>x.ip===ip);if(!c||!c.mac)return;try{await V.call(c.status==='已拉黑'?'clients-unblock':'clients-block',[c.mac]);await V.refresh();toast('终端黑名单已更新');}catch(e){toast('终端操作失败：'+e.message);}};
window.kickClientDevice=function(ip){const c=(P.state.clients||[]).find(x=>x.ip===ip);if(!c)return;openModal('终端网络阻断确认','<p>此后端不支持单次无线 deauth；将按 MAC 建立持久拉黑规则。</p><p>'+esc(c.name)+' · '+esc(c.mac||'')+'</p><div class="sim-modal-actions"><button class="sim-btn" onclick="closeModal()">取消</button><button class="sim-btn danger" data-ip="'+esc(ip)+'" onclick="window.confirmKickClient(this.dataset.ip)">确认拉黑</button></div>');};
window.confirmKickClient=async function(ip){const c=(P.state.clients||[]).find(x=>x.ip===ip);if(!c||!c.mac)return;try{await V.call('clients-block',[c.mac]);closeModal();await V.refresh();toast('终端已加入 MAC 拉黑列表');}catch(e){toast('拉黑失败：'+e.message);}};
window.addClientToParental=async function(ip){const c=(P.state.clients||[]).find(x=>x.ip===ip)||P.state.clients[0];if(!c||!c.mac)return;try{await V.call('parent-set',[c.mac,'1,2,3,4,5','21:30','07:00']);closeModal();await V.loadExtra();renderPage('家长控制');toast('已添加工作日家长控制规则');}catch(e){toast('添加规则失败：'+e.message);}};
window.addManualParentalRule=async function(){const ip=document.getElementById('parental-device-select')?.value||'',c=(P.state.clients||[]).find(x=>x.ip===ip)||P.state.clients[0],start=document.getElementById('parental-start-time')?.value||'21:30',end=document.getElementById('parental-end-time')?.value||'07:00';if(!c||!c.mac)return;try{await V.call('parent-set',[c.mac,'1,2,3,4,5',start,end]);await V.loadExtra();renderPage('家长控制');toast('家长控制规则已写入');}catch(e){toast('规则保存失败：'+e.message);}};
window.removeParentalRule=async function(i){const r=P.state.parentalRules?.[i];if(!r)return;try{await V.call('parent-clear',[r.mac]);await V.loadExtra();renderPage('家长控制');toast('规则已解除');}catch(e){toast('解除失败：'+e.message);}};
window.clearAllParentalRules=async function(){const a=[...(P.state.parentalRules||[])];try{for(const r of a)await V.call('parent-clear',[r.mac]);await V.loadExtra();closeModal();renderPage('家长控制');toast('全部规则已解除');}catch(e){toast('批量解除中断：'+e.message);}};
window.setClientQos=function(){toast('当前固件没有已验证的单终端 QoS 后端接口，未修改规则。');};
window.saveClientLimit=function(){toast('当前版本没有已验证的单终端限速接口，已阻止模拟保存。');};
window.setWorkMode=function(){openModal('工作模式保护','<div class="sim-notice warning">为保护现网 PPPoE、VLAN 2044、IPv6 和交换机拓扑，当前仅显示模式，不开放模式切换。</div>');};

window.setLedBright=async function(v){try{await V.call('matrix-set',['light_level',String(v)]);matrixState.bright=Number(v);window.drawAthenaMatrix?.();toast('点阵屏亮度已更新');}catch(e){toast('设置失败：'+e.message);}};
window.toggleLedNightMode=async function(v){try{await V.call('matrix-set',['night',v?1:0]);matrixState.nightModeEnabled=!!v;toast('夜间模式已更新');}catch(e){toast('设置失败：'+e.message);}};
window.setLedNightTime=async function(t,v){try{await V.call('matrix-set',[t==='start'?'night_start':'night_end',v]);matrixState[t==='start'?'nightStart':'nightEnd']=v;toast('夜间时段已更新');}catch(e){toast('设置失败：'+e.message);}};
window.setLedNightAction=async function(a){try{await V.call('matrix-set',['night_level',a==='off'?0:1]);matrixState.nightAction=a;toast('夜间策略已更新');}catch(e){toast('设置失败：'+e.message);}};
window.toggleLedPower=async function(){const v=!matrixState.power;try{await V.call('matrix-set',['enabled',v?1:0]);matrixState.power=v;window.drawAthenaMatrix?.();toast(v?'点阵屏已开启':'点阵屏已关闭');}catch(e){toast('设置失败：'+e.message);}};
window.setLedChan=function(c){matrixState.chan=c;window.drawAthenaMatrix?.();toast('频道切换仅改变预览，未写入硬件');};
window.toggleLedAutoLoop=function(){toast('自动轮播仅为预览效果，未接入硬件任务。');};
window.toggleLedLoopItem=function(){toast('轮播列表仅为预览设置。');};
window.setLedCustomText=function(){toast('自定义文本尚无设备端接口，未保存。');};
window.setLedAmbientColor=function(){toast('硬件接口未提供氛围灯颜色控制。');};

window.installNas=async function(s){const m=String(s||'ksmbd').toLowerCase().includes('samba')?'samba4':'ksmbd';try{const r=await V.call('nas-install',[m]);await V.loadExtra();renderPage('NAS 文件共享');toast(r.msg||'NAS 已安装');}catch(e){toast('安装失败：'+e.message);}};
window.uninstallNas=function(){openModal('卸载 NAS 确认','<div class="sim-notice warning">仅卸载 Athena 管理的软件包，不应删除 USB 文件数据。</div><div class="sim-modal-actions"><button class="sim-btn" onclick="closeModal()">取消</button><button class="sim-btn danger" onclick="window.AthenaV1.removeNas()">确认卸载</button></div>');};
window.execDiag=async function(){const c=document.getElementById('simDiagCmd')?.value||'ping',h=document.getElementById('simDiagHost')?.value||'223.5.5.5',o=document.getElementById('simDiagOut');try{const a=c==='dns'?'diag-dns':c==='check'?'diag-check':'diag-ping',r=await V.call(a,a==='diag-check'?[]:[h]);if(o)o.textContent=JSON.stringify(r,null,2);toast('诊断已由路由器执行');}catch(e){if(o)o.textContent=e.message;toast('诊断失败：'+e.message);}};

const dow=()=>{const s=P.state.rebootSchedule||{},f=s.freq||'daily';if(f==='weekly'){const n=Number(s.day||1);return String(n===7?0:n);}if(f==='workdays')return'1,2,3,4,5';if(f==='weekends')return'0,6';return'*';};
const syncReboot=async()=>{const s=P.state.rebootSchedule||{};if(!s.enabled)return;try{await V.call('reboot-enable',[s.time||'04:00',dow()]);await V.loadExtra();}catch(e){toast('定时重启保存失败：'+e.message);}};
window.toggleRebootSchedule=async function(v){const s=P.state.rebootSchedule||(P.state.rebootSchedule={});s.enabled=!!v;if(!v){try{await V.call('reboot-disable');await V.loadExtra();toast('定时重启已关闭');}catch(e){toast('关闭失败：'+e.message);}return;}await syncReboot();};
window.setRebootFreq=function(v){P.state.rebootSchedule.freq=v;if(P.state.rebootSchedule.enabled)syncReboot();};
window.setRebootDay=function(v){P.state.rebootSchedule.day=v;if(P.state.rebootSchedule.enabled)syncReboot();};
window.setRebootTime=function(v){P.state.rebootSchedule.time=v;if(P.state.rebootSchedule.enabled)syncReboot();};
window.toggleRebootDelay=function(){toast('后端不支持设备忙时延迟条件，未启用。');};

window.createNewBackup=async function(auto=true){try{const r=await V.call('backup-create');await V.loadExtra();renderPage('系统维护与备份');toast('已创建路由器配置备份：'+(r.file||'完成'));if(auto&&r.file)await V.downloadBackup(r.file);}catch(e){toast('备份失败：'+e.message);}};
window.downloadBackupFile=async function(i){const b=P.state.backups?.[i];if(!b)return;try{await V.downloadBackup(b.name);}catch(e){toast('下载失败：'+e.message);}};
window.deleteBackupFile=function(i){const b=P.state.backups?.[i];if(!b)return;openModal('删除备份确认','<p>确认删除 '+esc(b.name)+'？</p><div class="sim-modal-actions"><button class="sim-btn" onclick="closeModal()">取消</button><button class="sim-btn danger" onclick="window.confirmDeleteBackup('+i+')">确认删除</button></div>');};
window.confirmDeleteBackup=async function(i){const b=P.state.backups?.[i];if(!b)return;try{await V.call('backup-delete',[b.name]);closeModal();await V.loadExtra();renderPage('系统维护与备份');toast('备份已删除');}catch(e){toast('删除失败：'+e.message);}};
window.triggerRestoreBackup=function(){window.AthenaV1.restoreBackup('');};
window.confirmUsbFormat=function(){const p=[];(P.state.disks||[]).forEach(d=>(d.parts||[]).forEach(x=>{if(x.name&&x.mount==='')p.push('/dev/'+x.name);}));if(!p.length){toast('未发现未挂载 USB 分区');return;}const opts=p.map(x=>'<option>'+esc(x)+'</option>').join('');openModal('USB 分区格式化确认','<div class="sim-notice warning">格式化不可逆；后端会再次校验 USB 分区、挂载状态和系统盘保护。</div><select id="v1-format-dev" class="sim-field">'+opts+'</select><select id="v1-format-fs" class="sim-field"><option>ext4</option><option>vfat</option><option>exfat</option><option>f2fs</option></select><input id="v1-format-confirm" class="sim-field" placeholder="输入 FORMAT"><div class="sim-modal-actions"><button class="sim-btn" onclick="closeModal()">取消</button><button class="sim-btn danger" onclick="window.AthenaV1.formatDisk()">确认格式化</button></div>');};
window.confirmReboot=function(){openModal('确认重启路由器','<div class="sim-notice warning">重启会中断网络连接。确认当前没有关键网络操作后再继续。</div><div class="sim-modal-actions"><button class="sim-btn" onclick="closeModal()">取消</button><button class="sim-btn danger" onclick="window.AthenaV1.rebootNow()">确认重启</button></div>');};
window.confirmFactoryReset=function(){openModal('恢复出厂设置已禁用','<div class="sim-notice warning">本版本不开放恢复出厂设置，以保护现网配置。</div>');};window.finalFactoryReset=window.confirmFactoryReset;
window.triggerFirmwareUpgrade=function(){openModal('固件刷写已禁用','<div class="sim-notice warning">本项目仅构建独立 LuCI APK，不在页面内刷写整套固件。</div>');};
window.installOpkgPackage=async function(n){try{const r=await V.call('packages-install',[n]);await V.loadExtra();renderPage('软件包管理');toast(r.msg||'软件包已安装');}catch(e){toast('安装失败：'+e.message);}};
window.removeOpkgPackage=function(n){const p=typeof opkgState!=='undefined'?(opkgState.installed||[]).find(x=>x.name===n):null;if(p&&p.protected){openModal('关键软件包保护','<div class="sim-notice warning">OpenClash、NSS/ECM 和关键系统组件禁止卸载。</div>');return;}openModal('确认卸载软件包','<p>确认卸载 '+esc(n)+'？后端会再次检查依赖和关键包保护。</p><div class="sim-modal-actions"><button class="sim-btn" onclick="closeModal()">取消</button><button class="sim-btn danger" data-pkg="'+esc(n)+'" onclick="window.AthenaV1.removePackage(this.dataset.pkg)">确认卸载</button></div>');};
window.upgradeOpkgPackage=async function(n){try{const r=await V.call('packages-upgrade',[n]);await V.loadExtra();renderPage('软件包管理');toast(r.msg||'软件包已升级');}catch(e){toast('升级失败：'+e.message);}};
window.opkgUpdateLists=async function(){try{const r=await V.call('packages-update',[],120000);await V.loadExtra();renderPage('软件包管理');toast(r.msg||'软件包索引已更新');}catch(e){toast('更新列表失败：'+e.message);}};
window.upgradeAllOpkgPackages=function(){openModal('禁止全量升级','<div class="sim-notice warning">禁止全量升级，以免影响内核、NSS/ECM、OpenClash、PPPoE 和网络组件。</div>');};
window.openOpkgUploadModal=function(){toast('未开放任意软件包文件上传安装');};window.handleMockIpkUpload=window.openOpkgUploadModal;window.triggerManualOpkgInstall=window.openOpkgUploadModal;

V.action=async function(cmd){
 if(P&&P.mode!=='device')return commandHandler(cmd);
 if(cmd==='ping'||cmd==='dns-query'||cmd==='nslookup'){const h=(document.getElementById(cmd==='ping'?'diagTarget':'dnsQuery')?.value||'223.5.5.5').trim(),r=await V.call(cmd==='ping'?'diag-ping':'diag-dns',[h]),o=document.getElementById(cmd==='ping'?'diagOutput':'dnsResult');if(o)o.textContent=JSON.stringify(r,null,2);return;}
 if(cmd==='reboot'){window.confirmReboot();return;}if(cmd==='backup-create'){await window.createNewBackup(false);return;}
 if(cmd==='backup-download'){if(P.state.backups?.length)await window.downloadBackupFile(0);else toast('当前没有备份');return;}
 if(cmd==='backup-restore'){window.triggerRestoreBackup();return;}if(cmd==='storage-check'){await V.loadExtra();toast('存储清单已刷新');return;}
 if(cmd==='log-refresh'){await V.loadExtra();toast('系统日志已刷新');return;}
 if(['factory-reset','upgrade','storage-format','trace','wan-disconnect','wan-reconnect','backup-verify'].includes(cmd)){openModal('操作未开放','<div class="sim-notice warning">该操作需要独立的参数校验或设备验收。本版本已阻止执行。</div>');return;}
 return commandHandler(cmd);
};
document.querySelectorAll('[data-command]').forEach(b=>{b.onclick=()=>V.action(b.dataset.command).catch(e=>toast(e.message||'操作失败'));});
})();
