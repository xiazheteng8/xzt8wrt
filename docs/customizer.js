/* Exact package selection shared with plugin_support.py; no credentials in browser. */
let customMode=query.get('mode')==='custom', pluginCatalog=null, pluginError='', signature='', signatureKey='', chosen=new Set((query.get('plugins')??'luci-app-passwall2,luci-app-ssr-plus').split(',').filter(Boolean));
const uid=()=>selected.uid||selected.target.replaceAll(' ','')+'/'+selected.id;
const customSection=document.createElement('section');
customSection.className='panel';
customSection.innerHTML='<div class="panel-head"><h2>🧩 自选插件</h2><label><input type="checkbox" id="custom-mode"> 启用自选</label></div><div class="config-body"><p class="mini-note">参考 openwrt.ai 常用插件。LuCI、WOL、DDNS-GO 为基础组件；未适配项不可选。固定精简版 / 高大全版保持原配方。</p><div id="custom-controls" hidden><input id="plugin-search" type="search" placeholder="搜索插件，如 PassWall、下载、DNS" aria-label="搜索插件" style="width:100%;padding:9px;margin:12px 0;border:1px solid #d8e1d7;border-radius:6px"><div id="plugin-options" style="max-height:330px;overflow:auto"></div><p id="custom-selection" class="mini-note"></p><label>构建方式 <select id="custom-method"><option value="auto">自动：优先快速组装，缺包时源码构建</option><option value="fast">只用官方预编译组件（失败时不回退）</option><option value="source">从源码构建（较慢）</option></select></label><p class="mini-note">PassWall 2 / SSR Plus+ 当前使用固定提交的外部源码，自动模式会走源码构建；同装的代理默认关闭自启，配置后再启用。</p></div></div>';
document.querySelector('.center').insertBefore(customSection,document.getElementById('downloads'));
const customModal=document.createElement('div');
customModal.innerHTML='<div class="summary-row"><span>plugins</span><strong id="modal-plugins" style="white-space:pre-wrap;overflow-wrap:anywhere"></strong></div><div class="summary-row"><span>method</span><strong id="modal-method"></strong></div>';
$('modal-profile').parentElement.after(customModal);
const originalRender=render, originalDownload=renderDownload, originalLinks=updateLinks;
const oldInstructions=$('build-modal').querySelector('ol').innerHTML, oldNotice=$('build-modal').querySelector('.notice').textContent;
function pluginList(){if(!pluginCatalog){$('plugin-options').textContent=pluginError||'正在读取插件目录…';return}const search=$('plugin-search').value.trim().toLowerCase();$('plugin-options').replaceChildren();for(const plugin of pluginCatalog.plugins){if(!`${plugin.id} ${plugin.name}`.toLowerCase().includes(search))continue;const label=document.createElement('label');label.style.cssText='display:flex;gap:9px;padding:8px 2px;border-bottom:1px solid #edf1e9;align-items:flex-start;font-size:12px';const box=document.createElement('input');box.type='checkbox';box.disabled=!plugin.supported;box.checked=chosen.has(plugin.id);box.setAttribute('aria-label',plugin.name+' ('+plugin.id+')');box.addEventListener('change',()=>{box.checked?chosen.add(plugin.id):chosen.delete(plugin.id);render()});const text=document.createElement('span');text.textContent=plugin.name+' · '+plugin.id+(plugin.supported?(plugin.external?' · 外部源码，待完整构建验证':''):' · 当前未适配');label.append(box,text);$('plugin-options').append(label)}}
function customParams(){return `device: ${uid()}\nplugins: ${[...chosen].sort().join(',')}\nmethod: ${$('custom-method').value}\nversion: ${typeof chosenVersion==='undefined'?'latest':chosenVersion}\nconfigure_only: false\n工作流：${base()}/actions/workflows/custom.yml`}
async function refreshSignature(){const key=uid()+'\n'+[...chosen].sort().join(',')+'\nv1';if(signatureKey===key&&signature)return;signatureKey=key;signature='';const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(key));if(signatureKey!==key)return;signature=[...new Uint8Array(digest)].map(b=>b.toString(16).padStart(2,'0')).join('').slice(0,32);renderDownload()}
function customRender(){
 $('custom-mode').checked=customMode;$('custom-controls').hidden=!customMode;customModal.hidden=!customMode;
 $('modal-platform').parentElement.hidden=customMode;$('modal-profile').parentElement.hidden=customMode;
 $('plugin-list').hidden=customMode;$('plugin-list').previousElementSibling.hidden=customMode;$('plugins-detail').closest('details').hidden=customMode;
 if(!customMode){$('build-modal').querySelector('ol').innerHTML=oldInstructions;$('build-modal').querySelector('.notice').textContent=oldNotice;return}
 $('compatibility').textContent=selected.kind==='hard'?'自选插件需符合该设备闪存限制，容量不足时任务会失败。':'自选以基础组件为起点，根分区 512 MiB。';
 $('build-modal').querySelector('.notice').textContent='这是单设备自选构建。自动模式可回退到数小时的源码编译；新插件接入仍需完整构建与实机验证。';
 $('summary-profile').textContent='自选插件 · '+chosen.size+' 项';$('summary-proxy').textContent=[...chosen].filter(p=>['luci-app-passwall','luci-app-passwall2','luci-app-ssr-plus'].includes(p)).map(p=>p.replace('luci-app-','')).join(' + ')||'未选择代理';
 $('custom-selection').textContent=`已选 ${chosen.size} 项：${[...chosen].sort().join(', ')||'仅基础组件'}`;
 $('modal-device-row').hidden=false;$('modal-device').textContent=uid();$('modal-plugins').textContent=[...chosen].sort().join(',')||'（留空，仅基础组件）';$('modal-method').textContent=$('custom-method').value;
 $('open-workflow').href=base()+'/actions/workflows/custom.yml';
 $('build-modal').querySelector('ol').innerHTML='<li>先下载下方完全匹配的已编译包；没有时再打开 <code>Customize firmware</code> 工作流。</li><li>点击 <code>Run workflow</code>，选择 <code>main</code>，照抄 device、plugins 和 method。</li><li>首次外部插件建议勾选 <code>configure_only</code> 检查配置；要生成固件则不要勾选。</li><li>构建成功后自动发布；相同设备与勾选组合会优先显示已有下载。网页不会直接启动任务。</li>';
 const params=new URLSearchParams({device:deviceKey(selected),profile:'lite',mode:'custom',plugins:[...chosen].sort().join(',')});history.replaceState(null,'',location.pathname+'?'+params);
 refreshSignature();pluginList();
}
render=function(){if(customMode)profile='lite';originalRender();customRender()};
updateLinks=function(){originalLinks();if(customMode)$('open-workflow').href=base()+'/actions/workflows/custom.yml'};
renderDownload=function(){if(!customMode)return originalDownload();if(!releaseLoaded){emptyDownload('正在查找完全匹配的成品…','优先下载已有固件，不重复构建。');return}if(releaseError){emptyDownload('暂时无法查询已发布镜像',releaseError);return}if(!signature){emptyDownload('正在计算插件组合…','正在匹配准确设备与插件清单。');return}const suffix=`-${selected.platform}-${selected.id}-custom-${signature}.zip`;const found=releases.flatMap(r=>(r.assets||[]).map(a=>({asset:a,release:r}))).find(v=>v.asset.name.endsWith(suffix));if(!found){emptyDownload('暂无完全匹配的自选成品','可以在 GitHub 使用上述插件组合构建；自动模式优先 ImageBuilder，缺包或失败时改用源码。');return}const box=document.createElement('div');box.className='download-item';const title=document.createElement('strong');title.textContent='✓ 已有完全匹配的自选固件';const detail=document.createElement('p');detail.textContent=selected.name+' · '+chosen.size+' 项自选插件 · '+(found.asset.size/1024/1024).toFixed(1)+' MiB';const link=document.createElement('a');link.className='primary';link.href=found.asset.browser_download_url;link.textContent='直接下载，无需重编译 ↓';link.target='_blank';link.rel='noopener';box.append(title,detail,link);$('download-result').replaceChildren(box)};
$('custom-mode').addEventListener('change',()=>{customMode=$('custom-mode').checked;if(customMode)profile='lite';signatureKey='';render()});
$('plugin-search').addEventListener('input',pluginList);$('custom-method').addEventListener('change',customRender);
for(const id of ['full-button','lite-button'])$(id).addEventListener('click',()=>{customMode=false},true);
$('copy-params').addEventListener('click',event=>{if(!customMode)return;event.stopImmediatePropagation();copy(customParams())},true);
fetch('plugins.json').then(r=>{if(!r.ok)throw Error();return r.json()}).then(c=>{pluginCatalog=c;const available=new Set(c.plugins.filter(p=>p.supported).map(p=>p.id));chosen=new Set([...chosen].filter(p=>available.has(p)));render()}).catch(()=>{pluginError='插件目录读取失败，请刷新后再试。';pluginList()});
render();
