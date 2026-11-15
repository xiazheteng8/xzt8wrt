/* Platform/model/version/image selectors and fixed public release policy. */
let popularPolicy=null, imageFormat=query.get('format')||'img', chosenVersion=query.get('version')||'latest';
let platformFilter=selected.platform;
const selectorBox=document.createElement('div');selectorBox.style.cssText='padding:0 18px 14px;display:grid;gap:8px;font-size:12px';
selectorBox.innerHTML='<label>平台<select id="platform-select" aria-label="选择平台" style="width:100%;padding:7px"></select></label><label>型号<select id="model-select" aria-label="选择型号" style="width:100%;padding:7px"></select></label><label>源码版本<select id="source-version" aria-label="选择源码版本" style="width:100%;padding:7px"><option value="latest">最新正式稳定版（自动跟随）</option><option value="25.12.2">ImmortalWrt 25.12.2</option></select></label><label id="image-format-row">x86 镜像类型<select id="image-format" aria-label="选择镜像类型" style="width:100%;padding:7px"><option value="img">IMG · 物理机 / 通用写盘</option><option value="qcow2">QCOW2 · PVE / KVM</option><option value="vmdk">VMDK · VMware</option><option value="vdi">VDI · VirtualBox</option><option value="vhdx">VHDX · Hyper-V</option></select></label>';
$('search-input').closest('.search').before(selectorBox);
if(!['img','qcow2','vmdk','vdi','vhdx'].includes(imageFormat))imageFormat='img';
if(!['latest','25.12.2'].includes(chosenVersion))chosenVersion='latest';
const installCard=document.createElement('section');installCard.className='panel';installCard.hidden=true;
installCard.innerHTML='<div class="panel-head"><h2>📦 首次安装 / 中间固件</h2></div><div class="config-body"><p id="intermediate-note" class="mini-note"></p><a id="vendor-intermediate" class="primary" target="_blank" rel="noopener">Cudy 官方下载页 ↗</a><a href="https://www.cudy.com/blogs/faq/openwrt-software-download" target="_blank" rel="noopener" class="secondary">厂商 OpenWrt 中间固件说明 ↗</a><p class="mini-note">链接由厂商提供，本项目不冒充厂商中间固件。256MB 与 128MB、不同生产批次及 stock/ubootmod 不能混刷。</p></div>';
$('downloads').after(installCard);
const versionRow=document.createElement('div');versionRow.className='summary-row';versionRow.innerHTML='<span>version</span><strong id="modal-version"></strong>';$('modal-profile').parentElement.after(versionRow);
const earlierRender=render, earlierDownload=renderDownload;
function isPopular(){return popularPolicy?.devices.some(d=>d.uid===uid())||false}
function syncSelectors(){
 if(platformFilter&&selected.platform!==platformFilter)platformFilter=selected.platform;
 window.xztPlatformFilter=platformFilter;
 const groups=[...new Set(DEVICES.map(d=>d.platform))].sort();
 $('platform-select').replaceChildren();for(const value of ['',...groups]){const o=document.createElement('option');o.value=value;o.textContent=value||'全部平台';o.selected=value===platformFilter;$('platform-select').append(o)}
 $('model-select').replaceChildren();for(const d of DEVICES.filter(d=>!platformFilter||d.platform===platformFilter)){const o=document.createElement('option');o.value=deviceKey(d);o.textContent=d.name+' · '+d.id;o.selected=deviceKey(d)===deviceKey(selected);$('model-select').append(o)}
 $('source-version').value=chosenVersion;$('image-format-row').hidden=selected.platform!=='x86';if(selected.platform!=='x86')imageFormat='img';$('image-format').value=imageFormat;
 $('modal-version').textContent=chosenVersion;
 const params=new URLSearchParams(location.search);params.set('version',chosenVersion);params.set('format',imageFormat);history.replaceState(null,'',location.pathname+'?'+params);
 const cudy=selected.id.startsWith('cudy_tr3000');installCard.hidden=!cudy;
 if(cudy){const large=selected.id.includes('256mb');$('vendor-intermediate').href='https://www.cudy.com/pages/download-center/'+(large?'tr3000-256mb-1-0':'tr3000-1-0');$('intermediate-note').textContent=selected.id.includes('ubootmod')?'你选择了 ubootmod 布局。请先核对是否已完成对应引导改造；不能直接按 stock 流程刷入。':'从原厂系统迁移可能需要 Cudy 官方中间固件。2025 年末起存在新闪存批次，请在厂商页面按 SN、闪存容量与硬件版本确认文件。'}
 renderDevices();
}
function versionMatches(asset){return chosenVersion==='latest'||asset.name.startsWith('xzt8wrt-'+chosenVersion+'-')}
renderDownload=function(){
 if(popularPolicy&&!isPopular()){emptyDownload('此型号仅提供自行构建教程','不纳入本站固定 Releases；请 Fork 后按型号参数运行。构建产物在自己的 Actions 中下载。');return}
 if(imageFormat==='img'&&selected.platform!=='x86'){const saved=releases;releases=releases.map(r=>({...r,assets:(r.assets||[]).filter(versionMatches)}));try{return earlierDownload()}finally{releases=saved}}
 if(!releaseLoaded){emptyDownload('正在查询虚拟机镜像…','只展示已实际生成的镜像。');return}if(releaseError){emptyDownload('暂时无法读取下载列表',releaseError);return}
 if(customMode&&!signature){emptyDownload('正在匹配插件组合…','请稍候');return}
 const stem=`-x86-generic-${customMode?'custom-'+signature:profile==='full'?'高大全版':'精简版'}-${imageFormat}-`;
 const candidates=releases.flatMap(r=>(r.assets||[]).map(a=>({asset:a,release:r}))).filter(v=>versionMatches(v.asset)&&v.asset.name.includes(stem)&&/-(bios|uefi)-(squashfs|ext4)\.zip$/.test(v.asset.name));
 const seen=new Set();const found=candidates.filter(v=>{const key=v.asset.name.split(stem)[1];if(seen.has(key))return false;seen.add(key);return true});
 if(!found.length){emptyDownload('暂无独立的 '+imageFormat.toUpperCase()+' 镜像','正在生成分开的镜像下载；请稍后刷新。');return}
 const box=document.createElement('div');box.className='download-item';
 for(const {asset} of found){const boot=asset.name.includes('-uefi-')?'UEFI':'BIOS';const fs=asset.name.includes('-squashfs.')?'SquashFS':'ext4';const a=document.createElement('a');a.className='primary';a.style.marginBottom='8px';a.href=asset.browser_download_url;a.target='_blank';a.rel='noopener';a.textContent=`下载 ${imageFormat.toUpperCase()} · ${boot} · ${fs} ↓`;box.append(a)}
 const note=document.createElement('p');note.textContent='每个下载包只有对应的一份镜像，按需要选一个即可。';box.append(note);$('download-result').replaceChildren(box);

};
render=function(){earlierRender();syncSelectors();renderDownload()};
$('platform-select').addEventListener('change',()=>{platformFilter=$('platform-select').value;const d=DEVICES.find(d=>!platformFilter||d.platform===platformFilter);if(d)selected=d;render()});
$('model-select').addEventListener('change',()=>{const d=DEVICES.find(d=>deviceKey(d)===$('model-select').value);if(d)selected=d;render()});
$('source-version').addEventListener('change',()=>{chosenVersion=$('source-version').value;render()});$('image-format').addEventListener('change',()=>{imageFormat=$('image-format').value;render()});
$('copy-params').addEventListener('click',event=>{event.stopImmediatePropagation();const text=customMode?customParams():`platform: ${buildPlatform(selected)}\nprofile: ${profile}\n${selected.custom?'device: '+uid()+'\n':''}configure_only: false\n工作流：${base()}/actions/workflows/build.yml`;copy(text+'\nversion: '+chosenVersion)},true);
fetch('release-devices.json').then(r=>{if(!r.ok)throw Error();return r.json()}).then(p=>{popularPolicy=p;render()}).catch(()=>{});
render();
