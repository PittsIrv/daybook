'use strict';
const $ = s => document.querySelector(s);
const COLORS = {Focus:'#557f67', Gaming:'#c49a72', Social:'#dbab99', Video:'#d9bc82', Leisure:'#e3b39b', Utility:'#98b9c7', Mixed:'#b4b2c4', Unclassified:'#dce1dc'};
let data={days:[],warnings:[]}, selected='', scope='all_devices', range=7, expanded=false;
function readStore(key){try{return JSON.parse(localStorage.getItem(key)||'{}')}catch{return {}}}
let labels={}, preferences={goal:'understand',labels:{},feedback:{}}, notes=readStore('daybook.notes.v1');
function saveStore(key,value){try{localStorage.setItem(key,JSON.stringify(value));return true}catch{status('Browser storage is unavailable. Notes and labels will not persist.',true);return false}}
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function fmt(n){if(n<60)return `${Math.round(n)}s`;const m=Math.floor(n/60),h=Math.floor(m/60);return h?`${h}h ${m%60}m`:`${m}m`}
function dayDate(s){return new Date(s+'T12:00:00')}
function shortDate(s){return dayDate(s).toLocaleDateString('en-US',{month:'short',day:'numeric'})}
function stamp(s){return new Date(s).toLocaleString('en-US',{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'})}
function status(message,error=false){$('#status').textContent=message;$('#status').className=error?'error':''}
function scoped(){return data.days.filter(d=>d.device_scope===scope)}
function current(){return scoped().find(d=>d.date===selected)}
function category(name){const value=labels[name]||data.defaults?.[name]||'Unclassified';return Object.hasOwn(COLORS,value)?value:'Unclassified'}
function apps(d){const result=new Map();for(const entry of d.entries){const a=result.get(entry.name)||{name:entry.name,seconds:0,count:0};a.seconds+=entry.seconds;a.count++;result.set(a.name,a)}return [...result.values()].sort((a,b)=>b.seconds-a.seconds||a.name.localeCompare(b.name))}
function categories(d){const sums=Object.fromEntries(Object.keys(COLORS).map(c=>[c,0]));for(const a of apps(d))sums[category(a.name)]+=a.seconds;return sums}
function render(){
  const scopes=[...new Set(data.days.map(d=>d.device_scope))];
  if(!scopes.includes(scope))scope=scopes[0]||'all_devices';
  $('#scope').innerHTML=scopes.map(s=>`<option value="${esc(s)}" ${s===scope?'selected':''}>${s==='all_devices'?'All devices':esc(s)}</option>`).join('');
  renderReview();
  const days=scoped();if(!days.some(d=>d.date===selected))selected=days.at(-1)?.date||'';
  $('#day').innerHTML=[...days].reverse().map(d=>`<option value="${d.date}" ${d.date===selected?'selected':''}>${shortDate(d.date)}${d.complete?'':' · partial'}</option>`).join('');
  $('#updated').textContent='Files checked '+stamp(data.updated_at);
  $('#source-folder').textContent='iCloud input folder: '+data.source_folder;
  $('#warnings').textContent=data.warnings.length?`${data.warnings.length} export(s) skipped: `+data.warnings.map(w=>w.file+' — '+w.reason).join('; '):'';
  const d=current();if(!d){renderTrend();$('#date-title').textContent='Your first day starts here';$('#apps').innerHTML='<tr><td colspan="4" class="empty-row">Collect yesterday to load your first daily export.</td></tr>';$('#source-summary').textContent='No valid exports';return}
  $('#date-title').textContent=dayDate(selected).toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric'});
  $('#completeness').textContent=d.complete?'Completed-day query':'Partial snapshot';$('#completeness').className='badge'+(d.complete?'':' partial');
  $('#capture').textContent='Captured '+stamp(d.captured_at);
  $('#total').textContent=fmt(d.total_seconds);
  const priorDate=dayDate(selected);priorDate.setDate(priorDate.getDate()-1);const priorKey=`${priorDate.getFullYear()}-${String(priorDate.getMonth()+1).padStart(2,'0')}-${String(priorDate.getDate()).padStart(2,'0')}`;
  const prev=days.find(x=>x.date===priorKey&&x.complete);
  if(d.complete&&prev){const delta=d.total_seconds-prev.total_seconds;$('#change').textContent=delta===0?`Same reported time as ${shortDate(prev.date)}`:`${delta>=0?'↑':'↓'} ${fmt(Math.abs(delta))} ${delta>=0?'more':'less'} than ${shortDate(prev.date)}`}
  else $('#change').textContent=d.complete?'No completed export for the previous day':'Captured during the day · not a full-day total';
  const list=apps(d), top=list[0], cat=categories(d);
  $('#top-app').textContent=top?.name||'No activity';$('#top-detail').textContent=top?`${fmt(top.seconds)} · ${d.total_seconds?Math.round(top.seconds/d.total_seconds*100):0}% of reported activity`:'';
  $('#focus-total').textContent=fmt(cat.Focus);$('#focus-detail').textContent=cat.Focus?'Your classification · not measured deep work':'Classify apps below to begin';
  $('#category-bar').innerHTML=Object.entries(cat).map(([k,v])=>`<div title="${k}: ${fmt(v)}" style="width:${d.total_seconds?v/d.total_seconds*100:0}%;background:${COLORS[k]}"></div>`).join('');
  $('#categories').innerHTML=Object.entries(cat).map(([k,v])=>`<div class="category-line"><span><i style="background:${COLORS[k]}"></i>${k}</span><span>${fmt(v)}</span></div>`).join('');
  $('#insight').textContent='Defaults describe app types. Mixed tools such as Chrome and ChatGPT are not assumed to be work or leisure.';
  $('#note').value=notes[scope+'|'+selected]||'';$('#note-status').textContent='';
  $('#source-summary').textContent=`${days.length} recorded days · ${days.filter(x=>x.complete).length} completed-day queries`;
  $('#source-file').textContent=`Selected: ${d.source}. ${d.snapshot_count} export(s) available for this day/scope; one selected.${d.unparsed.length?' '+d.unparsed.length+' unparsed row(s) excluded from totals.':''}`;
  $('#raw').textContent=d.raw_activity_text;
  renderTrend();renderApps();
}
function renderTrend(){
  const days=scoped(), end=dayDate(data.yesterday), lookup=new Map(days.map(d=>[d.date,d]));let slots=[];
  for(let i=range-1;i>=0;i--){const dt=new Date(end);dt.setDate(dt.getDate()-i);const key=`${dt.getFullYear()}-${String(dt.getMonth()+1).padStart(2,'0')}-${String(dt.getDate()).padStart(2,'0')}`;slots.push({key,dt,d:lookup.get(key)})}
  const max=Math.max(1,...slots.map(s=>s.d?.total_seconds||0));
  $('#trend').className='trend'+(range>7?' dense':'');
  $('#trend').innerHTML=slots.map(({key,dt,d},i)=>`<div class="bar-slot"><span class="amount">${d?fmt(d.total_seconds):'—'}</span><button class="bar ${d?(d.complete?'':'partial'):'missing'} ${selected===key?'selected':''}" ${d?`data-day="${key}"`:'disabled'} style="height:${d?Math.max(4,d.total_seconds/max*153):4}px" title="${shortDate(key)}: ${d?fmt(d.total_seconds)+(d.complete?'':' (partial)'):'No export'}" aria-label="${shortDate(key)}: ${d?fmt(d.total_seconds):'No export'}"></button><span class="day-label">${range===7?dt.toLocaleDateString('en-US',{weekday:'short'}):i%5===0?dt.getDate():''}</span></div>`).join('');
  $('#trend').querySelectorAll('[data-day]').forEach(b=>b.addEventListener('click',()=>{selected=b.dataset.day;render()}));
}
function renderApps(){const d=current();if(!d)return;const query=$('#search').value.toLowerCase();const all=apps(d).filter(a=>a.name.toLowerCase().includes(query)), visible=expanded?all:all.slice(0,10);
  $('#apps').innerHTML=visible.map(a=>{const pct=d.total_seconds?a.seconds/d.total_seconds*100:0;return `<tr><td><div class="app-cell"><span class="app-icon">${esc(a.name[0].toUpperCase())}</span><div>${esc(a.name)}${a.count>1?`<small>${a.count} exported rows with this name</small>`:''}</div></div></td><td>${fmt(a.seconds)}</td><td><div class="progress-row"><div class="progress"><i style="width:${pct}%"></i></div><span>${pct.toFixed(1)}%</span></div></td><td><select data-app="${esc(a.name)}" aria-label="Category for ${esc(a.name)}">${Object.keys(COLORS).map(c=>`<option ${category(a.name)===c?'selected':''}>${c}</option>`).join('')}</select></td></tr>`}).join('')||'<tr><td colspan="4" class="empty-row">No matching activity.</td></tr>';
  $('#apps').querySelectorAll('[data-app]').forEach(s=>s.addEventListener('change',()=>{labels[s.dataset.app]=s.value;savePreferences()}));
  $('#show-all').hidden=all.length<=10;$('#show-all').textContent=expanded?'Show top 10 ↑':`View all ${all.length} apps & websites ↓`;
}
function adoptPreferences(){preferences=data.preferences;labels={...preferences.labels};}
async function savePreferences(){
  const controls=[...document.querySelectorAll('#goal,[data-app],[data-feedback],#quick-category,#reset-feedback')];
  controls.forEach(b=>b.disabled=true);
  try{const r=await fetch('/api/preferences',{method:'POST',headers:{'X-Daybook-Action':'collect','Content-Type':'application/json'},body:JSON.stringify({...preferences,labels})});const result=await r.json();if(!r.ok)throw Error(result.error);data=result;adoptPreferences();render();status('Saved on this Mac. Comparisons use the same labels across all dates.');}
  catch(e){status(e.message,true);await load();}finally{controls.forEach(b=>b.disabled=false)}
}
function renderReview(){
  const r=data.reviews?.[scope];if(!r)return;
  $('#goal').value=preferences.goal;
  $('#review-period').textContent=(data.demo?'SYNTHETIC DEMO · ':'')+shortDate(r.start)+' – '+shortDate(r.end)+' · Latest finished Monday–Sunday week';
  $('#review-message').textContent=r.message;
  $('#coverage').innerHTML=`<span>${r.recent_days}/7 recent days</span><span>${r.baseline_days}/28 baseline days</span><span>${r.ready?'Baseline ready':'Learning your routine'}</span>`;
  $('#review-method').textContent=r.method+' '+r.caveat;
  $('#findings').innerHTML=r.findings.map(f=>`<article class="finding"><div class="eyebrow">${esc(f.kind==='substitution'?'A SHIFT IN HABITS':f.kind==='weekday'?'A RECURRING PATTERN':'A MEANINGFUL CHANGE')}</div><h3>${esc(f.title)}</h3><p>${esc(f.detail)}</p>${f.suggestion?`<p class="suggestion">${esc(f.suggestion)}</p>`:''}<div class="finding-actions"><button data-feedback="useful" data-finding="${esc(f.id)}" aria-pressed="${preferences.feedback[f.id]==='useful'}">${preferences.feedback[f.id]==='useful'?'✓ Useful':'Useful'}</button><button data-feedback="hide" data-finding="${esc(f.id)}">Hide this pattern</button></div></article>`).join('');
  $('#findings').querySelectorAll('[data-feedback]').forEach(b=>b.addEventListener('click',()=>{preferences.feedback[b.dataset.finding]=b.dataset.feedback;savePreferences()}));
  const name=r.classification_candidate;
  $('#classification-help').innerHTML=name?`<label for="quick-category">Optional: <strong>${esc(name)}</strong> accounts for substantial unclassified time. One label helps future reviews.</label><select id="quick-category" aria-label="Category for ${esc(name)}">${Object.keys(COLORS).map(c=>`<option ${category(name)===c?'selected':''}>${c}</option>`).join('')}</select>`:'';
  if(name)$('#quick-category').addEventListener('change',()=>{labels[name]=$('#quick-category').value;savePreferences()});
  const c=data.collection;
  $('#collection-state').textContent=data.demo?'Demo only · real collection disabled':c.enabled?'Automatic collection enabled while Daybook runs · checks after 8 AM':'Automatic collection paused for this session';
  $('#collection-error').textContent=data.demo?'56 fictional days. Your personal files and settings are separate.':c.error?c.error:c.last_success?'Last successful collection: '+stamp(c.last_success):'First run may need approval in Shortcuts. Missing days stay visible.';
  $('#collect').disabled=!!data.demo||c.running;
}
$('#goal').addEventListener('change',()=>{preferences.goal=$('#goal').value;savePreferences()});
$('#reset-feedback').addEventListener('click',()=>{preferences.feedback={};savePreferences()});
async function load(){try{const response=await fetch('/api/data');if(!response.ok)throw Error('Could not read local exports');data=await response.json();adoptPreferences();render()}catch(e){status(e.message,true)}}
$('#refresh').addEventListener('click',async()=>{await load();if(data.days.length)status('Files refreshed. Repeated snapshots are counted once per day.')});
$('#collect').addEventListener('click',async()=>{const b=$('#collect');b.disabled=true;b.textContent='Collecting…';status('Running Screen Time Yesterday. If macOS asks for an existing shortcut permission, check Shortcuts.');try{const r=await fetch('/api/collect',{method:'POST',headers:{'X-Daybook-Action':'collect'}});const result=await r.json();if(!r.ok)throw Error(result.error);data=result;adoptPreferences();selected=data.yesterday;render();status('Yesterday’s export is saved and the dashboard is up to date.')}catch(e){status(e.message,true)}finally{b.disabled=false;b.textContent='↓ Collect yesterday'}});
$('#scope').addEventListener('change',()=>{scope=$('#scope').value;selected='';render()});$('#day').addEventListener('change',()=>{selected=$('#day').value;render()});
document.querySelectorAll('[data-range]').forEach(b=>b.addEventListener('click',()=>{range=Number(b.dataset.range);document.querySelectorAll('[data-range]').forEach(x=>x.classList.toggle('selected',x===b));renderTrend()}));
$('#search').addEventListener('input',renderApps);$('#show-all').addEventListener('click',()=>{expanded=!expanded;renderApps()});
$('#note').addEventListener('input',()=>{if(!selected)return;notes[scope+'|'+selected]=$('#note').value;if(saveStore('daybook.notes.v1',notes))$('#note-status').textContent='Saved in this browser'});
$('#csv').addEventListener('click',()=>{const d=current();if(!d)return;const cell=v=>'"'+String(v).replaceAll('"','""')+'"';const safe=v=>/^[=+\-@\t\r]/.test(String(v))?"'"+v:v;const rows=[['date','device_scope','name','reported_seconds','category','exported_rows','completed_day_query'],...apps(d).map(a=>[d.date,scope,safe(a.name),a.seconds,category(a.name),a.count,d.complete])];const blob=new Blob(['\uFEFF'+rows.map(r=>r.map(cell).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'});const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`daybook-${selected}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)});
load();
setInterval(()=>{if(!document.hidden&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName))load()},60000);
