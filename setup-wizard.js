'use strict';
'require view';
'require uci';
'require ui';
'require network';

function ipv4(s) {
 var a=String(s||'').split('.');
 if(a.length!==4||a.some(function(v){return !/^\d{1,3}$/.test(v)||+v>255;}))throw Error('请填写正确的 IPv4 地址');
 return a.reduce(function(n,v){return (n*256+(+v))>>>0;},0);
}
function asList(v){return Array.isArray(v)?v:typeof v==='string'?v.split(/\s+/).filter(Boolean):[];}
function planSetup(v, snapshot, names) {
 var ops=[], mode=v.mode, ip=ipv4(v.ip), prefix=+v.prefix;
 if(!['bypass','dhcp','pppoe'].includes(mode))throw Error('请选择工作模式');
 if(!Number.isInteger(prefix)||prefix<8||prefix>30)throw Error('子网前缀需在 8 至 30 之间');
 var mask=(0xffffffff<<(32-prefix))>>>0, host=(ip&~mask)>>>0;
 if(host===0||host===(~mask>>>0)||(ip>>>24)===0||(ip>>>24)>=224||ip>>>24===127)throw Error('管理 IP 必须是可用的单播主机地址');
 if(!snapshot.lan)throw Error('未找到 LAN 接口，请先在网络接口中创建 LAN');
 var set=function(c,s,k,value){ops.push(['set',c,s,k,value]);}, unset=function(c,s,k){ops.push(['unset',c,s,k]);};
 set('network','lan','proto','static');set('network','lan','ipaddr',[v.ip+'/'+prefix]);unset('network','lan','netmask');
 set('network','lan','defaultroute','1');
 var dns=String(v.dns||'').trim().split(/[\s,]+/).filter(Boolean);
 dns.forEach(ipv4);
 if(mode==='bypass'){
  var gw=ipv4(v.gateway);
  if(gw===ip)throw Error('管理 IP 不能与上级网关相同，请为旁路由选择一个空闲 IP（例如 192.168.11.2）');
  if((gw&mask)!==(ip&mask))throw Error('上级网关和管理 IP 必须在同一子网；请核对网段');
  if((gw&~mask)===0||(gw&~mask)===(~mask>>>0))throw Error('网关必须是可用主机地址');
  set('network','lan','gateway',v.gateway);set('network','lan','dns',dns.length?dns:[v.gateway]);
  ['wan','wan6'].forEach(function(n){if(snapshot[n]){set('network',n,'proto','none');set('network',n,'auto','0');['device','ifname','gateway','dns'].forEach(function(k){unset('network',n,k);});}});
  set('dhcp','lan','ignore','1');['ra','dhcpv6','ndp'].forEach(function(k){set('dhcp','lan',k,'disabled');});
 }else{
  if(!names.includes(v.wan))throw Error('请选择实际存在的 WAN 网口');
  var bridge=snapshot.bridge, ports=bridge?asList(bridge.ports):asList(snapshot.lan.device||snapshot.lan.ifname);
  if(ports.includes(v.wan)){
   var remaining=ports.filter(function(n){return n!==v.wan;});
   if(!bridge||!remaining.length)throw Error('此网口是唯一的 LAN 管理连接，不能同时改成 WAN。单网口请选旁路由；拨号或主路由请先添加独立网卡/VLAN。');
   set('network',bridge['.name'],'ports',remaining);
  }
  if(v.mode==='pppoe'&&(!v.username||!v.password))throw Error('请填写运营商宽带账号和密码');
  unset('network','lan','gateway');unset('network','lan','dns');
  set('network','wan','device',v.wan);unset('network','wan','ifname');set('network','wan','proto',mode);
  set('network','wan','defaultroute','1');set('network','wan','auto','1');
  if(dns.length){set('network','wan','peerdns','0');set('network','wan','dns',dns);}else{set('network','wan','peerdns','1');unset('network','wan','dns');}
  if(mode==='pppoe'){set('network','wan','username',v.username);set('network','wan','password',v.password);}
  else{unset('network','wan','username');unset('network','wan','password');}
  set('dhcp','lan','ignore','0');set('dhcp','lan','start','100');set('dhcp','lan','limit','100');set('dhcp','lan','leasetime','12h');
  // IPv6 remains disabled until explicitly configured, preventing stale RA/DHCPv6 advertisements.
  ['ra','dhcpv6','ndp'].forEach(function(k){set('dhcp','lan',k,'disabled');});
 }
 return ops;
}
function planFirewall(v, snapshot) {
 var ops=[], zones=snapshot.zones||[], lan=zones.find(function(z){return z.name==='lan';});
 if(!lan)throw Error('未找到 LAN 防火墙区域');
 var set=function(s,k,value){ops.push(['set','firewall',s,k,value]);};
 var lanId=lan['.name'], owned=asList(snapshot.lan.device||snapshot.lan.ifname).concat(asList(snapshot.bridge&&snapshot.bridge.ports));
 set(lanId,'network',Array.from(new Set(asList(lan.network).concat(['lan']))));
 ['input','output','forward'].forEach(function(k){set(lanId,k,'ACCEPT');});
 set(lanId,'masq',v.mode==='bypass'&&v.nat?'1':'0');
 zones.filter(function(z){return z!==lan;}).forEach(function(z){
  if(asList(z.network).includes('lan'))set(z['.name'],'network',asList(z.network).filter(function(n){return n!=='lan';}));
  if(v.mode==='bypass'&&asList(z.device).some(function(d){return owned.includes(d);}))set(z['.name'],'device',asList(z.device).filter(function(d){return !owned.includes(d);}));
 });
 if(v.mode!=='bypass'){
  var wan=zones.find(function(z){return z.name==='wan';}), id=wan?wan['.name']:'xzt8wrt_wan';
  if(!wan){ops.push(['add','firewall','zone',id]);set(id,'name','wan');set(id,'input','REJECT');set(id,'output','ACCEPT');set(id,'forward','REJECT');}
  set(id,'network',Array.from(new Set(asList(wan&&wan.network).concat(['wan']))));set(id,'masq','1');set(id,'mtu_fix','1');
  if(!(snapshot.forwardings||[]).some(function(f){return f.src==='lan'&&f.dest==='wan';})){
   ops.push(['add','firewall','forwarding','xzt8wrt_lan_wan']);set('xzt8wrt_lan_wan','src','lan');set('xzt8wrt_lan_wan','dest','wan');
  }
 }
 return ops;
}
function planDNS(v, snapshot) {
 var ops=[], main=snapshot.dnsmasq;
 if(!main)throw Error('未找到 dnsmasq 配置');
 var set=function(c,s,k,value){ops.push(['set',c,s,k,value]);};
 var servers=String(v.dns||'').trim().split(/[\s,]+/).filter(Boolean);
 if(servers.length>4)throw Error('最多填写四个 DNS 上游');
 servers.forEach(function(a){var n=ipv4(a);if(a===v.ip||(n>>>24)===127||(n>>>24)===0||(n>>>24)>=224)throw Error('DNS 上游不能指向旁路由自己、环回地址或无效地址');});
 var sid=snapshot.smartdns?snapshot.smartdns['.name']:'xzt_dns';
 if(!snapshot.smartdns)ops.push(['add','smartdns','smartdns',sid]);
 set('smartdns',sid,'enabled',v.smartdns?'1':'0');
 var dnsId=main['.name'];
 set('dhcp',dnsId,'addnhosts',Array.from(new Set(asList(main.addnhosts).concat(['/tmp/xzt8wrt.hosts']))));
 if(v.smartdns){
  if(!servers.length)servers=['223.5.5.5','119.29.29.29'];
  [['port','6053'],['bind_device','1'],['bind_device_name','lo'],['ipv6_server','0'],['tcp_server','1'],['auto_set_dnsmasq','0'],['cache_size','1024'],['prefetch_domain','1'],['serve_expired','1'],['speed_check_mode','ping,tcp:443']].forEach(function(p){set('smartdns',sid,p[0],p[1]);});
  servers.forEach(function(address,i){var name='xzt_up'+(i+1);if(!(snapshot.smartServers||[]).some(function(s){return s['.name']===name;}))ops.push(['add','smartdns','server',name]);set('smartdns',name,'enabled','1');set('smartdns',name,'type','udp');set('smartdns',name,'ip',address);});
  (snapshot.smartServers||[]).filter(function(s){return /^xzt_up[1-4]$/.test(s['.name'])&&+s['.name'].slice(-1)>servers.length;}).forEach(function(s){set('smartdns',s['.name'],'enabled','0');});
  set('dhcp',dnsId,'server',['127.0.0.1#6053'].concat(servers));set('dhcp',dnsId,'noresolv','1');set('dhcp',dnsId,'strictorder','1');
 }else{
  set('dhcp',dnsId,'server',servers);set('dhcp',dnsId,'noresolv','0');set('dhcp',dnsId,'strictorder','0');
 }
 return ops;
}
return view.extend({
 load:function(){return Promise.all([uci.load('network'),uci.load('dhcp'),uci.load('firewall'),network.getDevices(),uci.changes(),uci.load('smartdns')]);},
 handleSaveApply:null,handleSave:null,handleReset:null,
 render:function(data){
  var self=this, devices=data[3].filter(function(d){return d.getName()!=='lo'&&['ethernet','vlan','switch'].includes(d.getType());}), names=devices.map(function(d){return d.getName();});
  var field=function(id,label,type,value){return E('div',{'class':'cbi-value'},[E('label',{'class':'cbi-value-title','for':id},label),E('div',{'class':'cbi-value-field'},[E('input',{'id':id,'type':type||'text','value':value||'','autocomplete':type==='password'?'new-password':'off','class':'cbi-input-text'})])]);};
  var old=asList(uci.get('network','lan','ipaddr'))[0]||'192.168.11.1/24', parts=old.split('/');
  var mode=E('select',{'id':'xzt-mode','class':'cbi-input-select'},[E('option',{'value':'bypass'},'旁路由 · 单网口也可用（保留 LAN，不创建 WAN）'),E('option',{'value':'dhcp'},'主路由 · WAN 从上级自动获取地址（DHCP）'),E('option',{'value':'pppoe'},'主路由 · 宽带拨号（PPPoE）')]);
  var wan=E('select',{'id':'xzt-wan','class':'cbi-input-select'},devices.map(function(d){return E('option',{'value':d.getName()},d.getName());}));
  if(names.includes(uci.get('network','wan','device')))wan.value=uci.get('network','wan','device');
  var wanBox=E('div',{},[E('p',{},'请选择连接光猫或上级路由器的 WAN 网口；它必须独立于当前 LAN 管理连接。'),E('label',{},['WAN 网口 ',wan])]);
  var account=E('div',{},[field('xzt-user','宽带账号'),field('xzt-pass','宽带密码','password')]);
  var gateway=field('xzt-gw','上级路由器 IP / 默认网关','text',uci.get('network','lan','gateway')||'');
  var smart=E('input',{'type':'checkbox','id':'xzt-smartdns','checked':(uci.sections('smartdns','smartdns')[0]||{}).enabled==='1'});
  var smartBox=E('label',{},[smart,' 启用预配置 SmartDNS（6053，本地 DNS 仍使用 53；含备用上游）']);
  var nat=E('input',{'type':'checkbox','id':'xzt-nat','checked':true});
  var natBox=E('label',{},[nat,' 为经过旁路由的设备启用 IPv4 NAT（同网段回程经过旁路由，通常建议开启）']);
  var note=E('p',{'class':'alert-message notice'},'');
  var sync=function(){var bypass=mode.value==='bypass';wanBox.hidden=bypass;account.hidden=mode.value!=='pppoe';gateway.hidden=!bypass;natBox.hidden=!bypass;note.textContent=bypass?'只使用现有 LAN：设置管理 IP、上级网关、DNS，关闭 DHCP/IPv6 通告。其他设备要经过它上网，还需把网关指向本机。群晖虚拟网卡须连接能访问上级路由器的外部虚拟交换机。':'主路由模式会启用 LAN DHCP、WAN NAT 和 LAN→WAN 转发。LAN 与上级 WAN 必须使用不同网段，例如上级 192.168.11.1 时，LAN 改成 192.168.12.1。单网口且无独立 VLAN 时，请选择旁路由。';};
  mode.addEventListener('change',sync);sync();
  var pending=Object.keys(data[4]||{}).some(function(k){return (data[4][k]||[]).length;});
  var go=E('button',{'class':'btn cbi-button-action','disabled':pending,'click':ui.createHandlerFn(this,function(){
   try{
    var val=function(id){return document.getElementById(id).value.trim();};
    var v={mode:mode.value,ip:val('xzt-ip'),prefix:val('xzt-prefix'),gateway:val('xzt-gw'),dns:val('xzt-dns'),wan:wan.value,nat:nat.checked,smartdns:smart.checked,username:val('xzt-user'),password:document.getElementById('xzt-pass').value};
    var snapshot={lan:uci.get('network','lan'),wan:uci.get('network','wan'),wan6:uci.get('network','wan6')};
    snapshot.bridge=uci.sections('network','device').find(function(d){return d.type==='bridge'&&d.name===snapshot.lan.device;});
    snapshot.zones=uci.sections('firewall','zone');snapshot.forwardings=uci.sections('firewall','forwarding');snapshot.dnsmasq=uci.sections('dhcp','dnsmasq')[0];snapshot.smartdns=uci.sections('smartdns','smartdns')[0];snapshot.smartServers=uci.sections('smartdns','server');
    var ops=planSetup(v,snapshot,names).concat(planFirewall(v,snapshot),planDNS(v,snapshot));
    var selectedLan=uci.sections('firewall','zone').find(function(z){return z.name==='lan';});
    if(!selectedLan)throw Error('未找到 LAN 防火墙区域，请先检查现有网络配置');
    var summary=[E('p',{},'模式：'+mode.options[mode.selectedIndex].text),E('p',{},'新管理地址：http://'+v.ip+'/；本地别名：http://xzt8.wrt/cgi-bin/luci/admin/setup'),E('p',{},'SmartDNS：'+(v.smartdns?'启用，本地 6053 + 备用上游':'关闭，使用填写的 DNS 或网络上游')),E('p',{},v.mode==='bypass'?'默认网关：'+v.gateway+'；DNS：'+(v.dns||v.gateway)+'；关闭 LAN DHCP；不创建 WAN':'WAN：'+v.wan+' / '+v.mode+'；启用 LAN DHCP 和 NAT'),E('p',{},'应用后网络会短暂中断。请连接新地址并确认；未在时限内确认会由 LuCI 回滚。拨号密码不会显示在此处。')];
    ui.showModal('确认网络设置',summary.concat([E('div',{'class':'right'},[E('button',{'class':'btn','click':ui.hideModal},'返回修改'),' ',E('button',{'class':'btn cbi-button-action','click':ui.createHandlerFn(self,function(){
     if(!uci.get('dhcp','lan'))uci.add('dhcp','dhcp','lan');uci.set('dhcp','lan','interface','lan');
     if(v.mode!=='bypass'&&!uci.get('network','wan'))uci.add('network','interface','wan');
     ops.forEach(function(o){if(o[0]==='add')uci.add(o[1],o[2],o[3]);else if(o[0]==='set')uci.set(o[1],o[2],o[3],o[4]);else uci.unset(o[1],o[2],o[3]);});
     return uci.save().then(function(){ui.hideModal();return ui.changes.init();}).then(function(){ui.changes.apply(true);});
    })},'保存并应用（带回滚）')]) ]));
   }catch(e){ui.addNotification(null,E('p',{},e.message),'error');}
  })},'下一步：检查配置');
  return E('div',{},[E('h2',{},'xzt8wrt · 上网设置向导'),E('p',{},'① 选择模式 → ② 填写地址 → ③ 检查并应用。建议先完成向导，再配置代理与 DNS 插件。'),pending?E('p',{'class':'alert-message warning'},'当前有未应用的配置。请先处理页面右上角的待应用更改，再刷新向导。'):E('span'),E('label',{},['工作模式 ',mode]),note,field('xzt-ip','本机管理 IP','text',parts[0]),field('xzt-prefix','子网前缀长度（通常 24）','number',parts[1]||'24'),gateway,field('xzt-dns','DNS 上游（SmartDNS 留空使用预设；关闭时由网关/DHCP提供）','text',asList(uci.get('network','lan','dns')).join(' ')),natBox,E('p',{},''),smartBox,wanBox,account,E('p',{},'访问 http://xzt8.wrt/cgi-bin/luci/admin/setup 需让客户端 DNS 指向本机，或在主路由添加相同本地解析。浏览器安全 DNS/DoH 可能绕过本地解析。默认管理 IP：192.168.11.1。如果上级路由器也是此地址，旁路由请改用未占用的地址，例如 192.168.11.2。'),E('p',{},'存储：x86 ext4 镜像会尝试扩展启动盘最后的根分区；新装 Docker 使用 /srv/docker，共享扩容后的剩余空间；虚拟机请先在宿主机扩大虚拟硬盘。其他分区、ARM 闪存和 SquashFS 不自动调整。'),go]);
 }
});
