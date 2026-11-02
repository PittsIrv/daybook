'use strict';
const $ = s => document.querySelector(s);
const COLORS = {Focus:'#557f67', Entertainment:'#dbab99', Other:'#b4b2c4', Untagged:'#dce1dc'};
const PURPOSES=['Focus','Entertainment','Other'];
let setupExpanded=false, pendingSignature='', scopeChosen=false;
let data={days:[],warnings:[]}, selected='', scope='', range=7, expanded=false;
let labels={}, preferences={labels:{}};
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function fmt(n){if(n<60)return `${Math.round(n)}s`;const m=Math.floor(n/60),h=Math.floor(m/60);return h?`${h}h ${m%60}m`:`${m}m`}
function dayDate(s){return new Date(s+'T12:00:00')}
function shortDate(s){return dayDate(s).toLocaleDateString('en-US',{month:'short',day:'numeric'})}
function stamp(s){return new Date(s).toLocaleString('en-US',{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'})}
function status(message,error=false){$('#status').textContent=message;$('#status').className=error?'error':''}
function scoped(){return data.days.filter(d=>d.device_scope===scope)}
function current(){return scoped().find(d=>d.date===selected)}
function category(name){return labels[name]||'Untagged'}
function apps(d){const result=new Map();for(const entry of d.entries){const a=result.get(entry.name)||{name:entry.name,seconds:0,counted:0,count:0,detail:false};a.seconds+=entry.seconds;a.counted+=entry.counted_seconds??entry.seconds;a.detail ||= !!entry.detail_only;a.count++;result.set(a.name,a)}return [...result.values()].sort((a,b)=>b.seconds-a.seconds||a.name.localeCompare(b.name))}
function categories(d){const sums=Object.fromEntries(Object.keys(COLORS).map(c=>[c,0]));for(const a of apps(d))sums[category(a.name)]+=a.counted;return sums}
function render(){
  $('#intro-kicker').textContent=data.demo?'FICTIONAL DEMO · YOUR DAY, IN HOURS AND MINUTES.':'YOUR DAY, IN HOURS AND MINUTES.';
  const scopes=[...new Set(data.days.map(d=>d.device_scope))];
  if(!scopeChosen&&scopes.some(s=>s.startsWith('Exporter')))scope=scopes.find(s=>s.startsWith('Exporter'));
  if(!scopes.includes(scope))scope=scopes[0]||'all_devices';
  $('#scope').innerHTML=scopes.map(s=>`<option value="${esc(s)}" ${s===scope?'selected':''}>${s==='all_devices'?'All devices':esc(s)}</option>`).join('');
  renderSetup();renderCollection();renderIntegrationStatus();
  const days=scoped();if(!days.some(d=>d.date===selected))selected=days.at(-1)?.date||'';
  $('#day').innerHTML=[...days].reverse().map(d=>`<option value="${d.date}" ${d.date===selected?'selected':''}>${shortDate(d.date)}${d.complete?'':' · partial'}</option>`).join('');
  $('#updated').textContent='Files checked '+stamp(data.updated_at);
  $('#source-folder').textContent='iCloud input folder: '+data.source_folder;
  $('#warnings').textContent=data.warnings.length?`${data.warnings.length} export(s) skipped: `+data.warnings.map(w=>w.file+' — '+w.reason).join('; '):'';
  const d=current();if(!d){renderComparisons();renderTimeline();renderTrend();$('#date-title').textContent='Your first day starts here';$('#apps').innerHTML='<tr><td colspan="4" class="empty-row">Collect yesterday to load your first daily export.</td></tr>';$('#source-summary').textContent='No valid exports';['total','focus-total','entertainment-total','other-total'].forEach(id=>$('#'+id).textContent='—');$('#totals-note').textContent='Totals appear as soon as your first export arrives. No baseline or weeks of history needed.';$('#categories').innerHTML='';$('#category-bar').innerHTML='';$('#change').textContent='Waiting for data';$('#capture').textContent='';$('#completeness').textContent='';$('#raw').textContent='';return}
  $('#date-title').textContent=dayDate(selected).toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric'});
  $('#completeness').textContent=d.complete?'Completed-day query':'Partial snapshot';$('#completeness').className='badge'+(d.complete?'':' partial');
  $('#capture').textContent='Captured '+stamp(d.captured_at);
  $('#total').textContent=fmt(d.total_seconds);
  const priorDate=dayDate(selected);priorDate.setDate(priorDate.getDate()-1);const priorKey=`${priorDate.getFullYear()}-${String(priorDate.getMonth()+1).padStart(2,'0')}-${String(priorDate.getDate()).padStart(2,'0')}`;
  const prev=days.find(x=>x.date===priorKey&&x.complete);
  if(d.complete&&prev){const delta=d.total_seconds-prev.total_seconds;$('#change').textContent=delta===0?`Same reported time as ${shortDate(prev.date)}`:`${delta>=0?'↑':'↓'} ${fmt(Math.abs(delta))} ${delta>=0?'more':'less'} than ${shortDate(prev.date)}`}
  else $('#change').textContent=d.complete?'No completed export for the previous day':'Captured during the day · not a full-day total';
  const cat=categories(d);
  $('#focus-total').textContent=fmt(cat.Focus);$('#entertainment-total').textContent=fmt(cat.Entertainment);$('#other-total').textContent=fmt(cat.Other);
  $('#totals-note').textContent=cat.Untagged?`${fmt(cat.Untagged)} is still untagged and included in the total. Choose its purpose once in App labels.`:'All reported time is assigned. Your labels are remembered for future days.';
  if(d.unparsed.length)$('#totals-note').textContent+=` ${d.unparsed.length} unparsed row(s) are excluded from these numbers.`;
  $('#category-bar').innerHTML=Object.entries(cat).map(([k,v])=>`<div title="${k}: ${fmt(v)}" style="width:${d.total_seconds?v/d.total_seconds*100:0}%;background:${COLORS[k]}"></div>`).join('');
  $('#categories').innerHTML=Object.entries(cat).filter(([k,v])=>k!=='Untagged'||v>0).map(([k,v])=>`<div class="category-line"><span><i style="background:${COLORS[k]}"></i>${k}</span><span>${fmt(v)}</span></div>`).join('');
  $('#insight').textContent='Focus means work or study according to your labels. Other covers life activities such as travel and food; it is excluded from Focus and Entertainment.';
  $('#source-summary').textContent=`${days.length} recorded days · ${days.filter(x=>x.complete).length} completed-day queries`;
  $('#source-file').textContent=`Selected: ${d.source}. ${d.snapshot_count} export(s) available for this day/scope; one selected.${d.unparsed.length?' '+d.unparsed.length+' unparsed row(s) excluded from totals.':''}`;
  $('#raw').textContent=d.raw_activity_text;
  if(d.website_detail_seconds)$('#totals-note').textContent+=` ${fmt(d.website_detail_seconds)} of website detail is excluded to avoid counting browser time twice.`;
  renderTrend();renderApps();renderComparisons();renderTimeline();
}
function renderTrend(){
  const days=scoped(), end=dayDate(selected||data.yesterday), lookup=new Map(days.map(d=>[d.date,d]));let slots=[];
  for(let i=range-1;i>=0;i--){const dt=new Date(end);dt.setDate(dt.getDate()-i);const key=`${dt.getFullYear()}-${String(dt.getMonth()+1).padStart(2,'0')}-${String(dt.getDate()).padStart(2,'0')}`;slots.push({key,dt,d:lookup.get(key)})}
  const max=Math.max(1,...slots.map(s=>s.d?.total_seconds||0));
  $('#trend').className='trend'+(range>7?' dense':'');
  $('#trend').innerHTML=slots.map(({key,dt,d},i)=>`<div class="bar-slot"><span class="amount">${d?fmt(d.total_seconds):'—'}</span><button class="bar ${d?(d.complete?'':'partial'):'missing'} ${selected===key?'selected':''}" ${d?`data-day="${key}"`:'disabled'} style="height:${d?Math.max(4,d.total_seconds/max*153):4}px" title="${shortDate(key)}: ${d?fmt(d.total_seconds)+(d.complete?'':' (partial)'):'No export'}" aria-label="${shortDate(key)}: ${d?fmt(d.total_seconds):'No export'}"></button><span class="day-label">${range===7?dt.toLocaleDateString('en-US',{weekday:'short'}):i%5===0?dt.getDate():''}</span></div>`).join('');
  $('#trend').querySelectorAll('[data-day]').forEach(b=>b.addEventListener('click',()=>{selected=b.dataset.day;render()}));
}
function renderApps(){const d=current();if(!d)return;const query=$('#search').value.toLowerCase();const all=apps(d).filter(a=>a.seconds>300&&a.name.toLowerCase().includes(query)), visible=expanded?all:all.slice(0,10);
  $('#apps').innerHTML=visible.map(a=>{const pct=d.total_seconds?a.counted/d.total_seconds*100:0;return `<tr><td><div class="app-cell"><span class="app-icon">${esc(a.name[0].toUpperCase())}</span><div>${esc(a.name)}${a.detail?'<small>Website detail · excluded from total</small>':''}${a.count>1?`<small>${a.count} exported rows with this name</small>`:''}</div></div></td><td>${fmt(a.seconds)}</td><td><div class="progress-row"><div class="progress"><i style="width:${pct}%"></i></div><span>${a.detail?'—':pct.toFixed(1)+'%'}</span></div></td><td><select data-app="${esc(a.name)}" aria-label="Category for ${esc(a.name)}">${category(a.name)==='Untagged'?'<option value="" disabled selected>Choose once…</option>':''}${PURPOSES.map(c=>`<option ${category(a.name)===c?'selected':''}>${c}</option>`).join('')}</select></td></tr>`}).join('')||'<tr><td colspan="4" class="empty-row">No matching activity.</td></tr>';
  $('#apps').querySelectorAll('[data-app]').forEach(s=>s.addEventListener('change',()=>{labels[s.dataset.app]=s.value;savePreferences()}));
  $('#show-all').hidden=all.length<=10;$('#show-all').textContent=expanded?'Show top 10 ↑':`View all ${all.length} apps & websites ↓`;
}
function adoptPreferences(){preferences=data.preferences;labels={...preferences.labels};}
function renderIntegrationStatus(){
  $('#integration-status').textContent='Screen Time Exporter: '+(data.exporter?.message||'Not connected')+(data.exporter?.last_sync?' · last run '+stamp(data.exporter.last_sync):'');
  $('#permission-path').textContent=data.exporter?.permission_binary||'Install the optional exporter using the integration setup guide.';
  $('#retry-exporter').disabled=!!data.demo;
  const c=data.calendar||{};
  $('#calendar-status').textContent=(c.mode==='snapshot'?'Calendar: imported snapshot; automatic sync is not connected. ':c.mode==='mac_calendar'?'Calendar: selected Mac calendars · refreshes every 15 minutes while Daybook runs. ':'Calendar: ')+(c.error||c.message||'Not connected')+(c.captured_at?' · updated '+stamp(c.captured_at):'');
  $('#connect-calendar').disabled=!!data.demo;
  $('#connect-calendar').textContent=c.mode==='mac_calendar'?'Choose calendars':'Connect calendars';
}
function renderComparisons(){
  const d=current();if(!d){$('#comparisons').innerHTML='<p>No day selected.</p>';return}
  const now={Total:d.total_seconds,...categories(d)};
  $('#comparisons').innerHTML='<p class="subtle">Same device and source. Other is excluded from both Focus and Entertainment. Partial days show totals without change claims.</p><div class="comparison-grid">'+(d.comparisons||[]).map(c=>`<article><h3>${esc(c.title)}</h3><p class="subtle">${c.dates.map(shortDate).join(' · ')}</p>${c.baseline?['Total','Focus','Entertainment','Other'].map(k=>{const delta=now[k]-c.baseline[k];return `<div class="comparison-line"><span>${k}</span><strong>${fmt(now[k])} <small>vs ${fmt(c.baseline[k])}</small></strong><span>${c.comparable?(delta===0?'No change':(delta>0?'+':'−')+fmt(Math.abs(delta))):'Partial day'}</span></div>`}).join(''):`<p class="empty-row">${c.available_days} of ${c.required_days} completed days available.</p>`}</article>`).join('')+'</div>';
}
function timeLabel(value){return new Date(value).toLocaleTimeString('en-US',{hour:'numeric',minute:'2-digit'})}
function renderTimeline(){
  const d=current();
  if(!d){$('#hourly').textContent='No recorded day selected.';$('#sessions').textContent='';$('#calendar-events').textContent='';return}
  const sessions=d.sessions||[];
  const grouped=new Map();
  for(const hour of d.hourly||[])grouped.set(new Date(hour.start).getTime(),new Map(hour.apps.map(a=>[a.name,a.seconds])));
  for(const s of d.hourly?[]:sessions){let cursor=new Date(s.start).getTime(),end=new Date(s.end).getTime();while(cursor<end){const key=Math.floor(cursor/3600000)*3600000,stop=Math.min(end,key+3600000);if(stop<=cursor)break;const values=grouped.get(key)||new Map();values.set(s.name,(values.get(s.name)||0)+(stop-cursor)/1000);grouped.set(key,values);cursor=stop}}
  $('#hourly').innerHTML=[...grouped].sort((a,b)=>a[0]-b[0]).map(([hour,values])=>{const visible=[...values].filter(([,seconds])=>seconds>300).sort((a,b)=>b[1]-a[1]);return visible.length?`<div class="hour-row"><time>${timeLabel(hour)} <small>${new Date(hour).toLocaleTimeString('en-US',{timeZoneName:'short'}).split(' ').at(-1)}</small></time><div>${visible.map(([name,seconds])=>`<span class="activity-chip"><i style="background:${COLORS[category(name)]}"></i>${esc(name)} <strong>${fmt(seconds)}</strong></span>`).join('')}</div></div>`:''}).join('')||(sessions.length?'<p>No app exceeded 5 minutes within an hour.</p>':'<p>Hourly records need Screen Time Exporter. Daily Shortcut totals cannot reconstruct when an app was used.</p>');
  $('#sessions').innerHTML=sessions.filter(s=>s.seconds>300).map(s=>`<div class="session-row"><time>${timeLabel(s.start)}–${timeLabel(s.end)}</time><span>${esc(s.name)}</span><strong>${fmt(s.seconds)}</strong></div>`).join('')||'<p>No sessions over 5 minutes available.</p>';
  const events=(d.calendar_events||[]).filter(e=>(new Date(e.end)-new Date(e.start))>300000);
  $('#calendar-events').innerHTML=events.map(e=>`<article class="calendar-event"><time>${timeLabel(e.start)}–${timeLabel(e.end)}</time><strong>${esc(e.title)}</strong><small>${esc(e.calendar||'Calendar')} · scheduled</small></article>`).join('')||'<p>No imported events over 5 minutes for this day.</p>';
  if(d.timeline_synthetic)$('#hourly').insertAdjacentHTML('afterbegin','<p class="subtle">Fictional session times for demonstration.</p>');
}
$('#retry-exporter').addEventListener('click',async()=>{try{const r=await fetch('/api/exporter/retry',{method:'POST',headers:{'X-Daybook-Action':'collect'}});const result=await r.json();if(!r.ok)throw Error(result.error);status(result.message)}catch(e){status(e.message,true)}});
$('#connect-calendar').addEventListener('click',async()=>{try{const r=await fetch('/api/calendar/connect',{method:'POST',headers:{'X-Daybook-Action':'collect'}});const result=await r.json();if(!r.ok)throw Error(result.error);status(result.message)}catch(e){status(e.message,true)}});
async function savePreferences(){
  const controls=[...document.querySelectorAll('[data-app],[data-purpose],#accept-suggestions')];
  controls.forEach(b=>b.disabled=true);
  try{const r=await fetch('/api/preferences',{method:'POST',headers:{'X-Daybook-Action':'collect','Content-Type':'application/json'},body:JSON.stringify({...preferences,labels})});const result=await r.json();if(!r.ok)throw Error(result.error);data=result;adoptPreferences();render();status('Label saved. Applied to past and future days; you can adjust it anytime.');}
  catch(e){status(e.message,true);await load();}finally{controls.forEach(b=>b.disabled=false)}
}
function pendingApps(){return (data.app_catalog||[]).filter(a=>a.scopes.includes(scope)&&!labels[a.name])}
function renderSetup(){
  const pending=pendingApps(), signature=scope+'|'+JSON.stringify(pending.map(a=>a.name));
  if(signature!==pendingSignature){$('#setup').open=!!pending.length;pendingSignature=signature;}
  $('#setup-title').textContent=pending.length?'New apps: choose their purpose once':'App labels are up to date';
  $('#setup-count').textContent=pending.length?`${pending.length} waiting`:'Saved automatically';
  $('#setup-list').innerHTML=(setupExpanded?pending:pending.slice(0,8)).map(a=>`<div class="setup-row"><div><strong>${esc(a.name)}</strong><small>First seen ${shortDate(a.first_seen)} · suggested: ${a.suggested_category}</small></div><div class="purpose-choices">${PURPOSES.map(c=>`<button data-app="${esc(a.name)}" data-purpose="${c}" aria-label="Mark ${esc(a.name)} as ${c}">${c}</button>`).join('')}</div></div>`).join('')||'<p>All known apps have a saved label. Change any label in the app breakdown whenever you want.</p>';
  $('#setup-list').querySelectorAll('[data-purpose]').forEach(b=>b.addEventListener('click',()=>{labels[b.dataset.app]=b.dataset.purpose;savePreferences()}));
  $('#setup-more').hidden=pending.length<=8;$('#setup-more').textContent=setupExpanded?'Show fewer':`Show all ${pending.length} new apps`;
  $('#setup-bulk').hidden=!pending.length;$('#accept-suggestions').textContent=`Use suggested labels for these ${pending.length} apps`;
}
function renderCollection(){
  const c=data.collection;
  $('#collection-state').textContent=data.demo?'Demo only · real collection disabled':c.enabled?'Automatic collection enabled while Daybook runs · checks after 8 AM':'Automatic collection paused for this session';
  $('#collection-error').textContent=data.demo?'56 fictional days. Your personal files and settings are separate.':c.error?c.error:c.last_success?'Last successful collection: '+stamp(c.last_success):'First run may need approval in Shortcuts. Missing days stay visible.';
  $('#collect').disabled=!!data.demo||c.running;
}
$('#setup-more').addEventListener('click',()=>{setupExpanded=!setupExpanded;renderSetup()});
$('#accept-suggestions').addEventListener('click',()=>{for(const a of pendingApps())labels[a.name]=a.suggested_category;savePreferences()});
async function load(){try{const response=await fetch('/api/data');if(!response.ok)throw Error('Could not read local exports');data=await response.json();adoptPreferences();render()}catch(e){status(e.message,true)}}
$('#refresh').addEventListener('click',async()=>{await load();if(data.days.length)status('Files refreshed. Repeated snapshots are counted once per day.')});
$('#collect').addEventListener('click',async()=>{const b=$('#collect');b.disabled=true;b.textContent='Collecting…';status('Running Screen Time Yesterday. If macOS asks for an existing shortcut permission, check Shortcuts.');try{const r=await fetch('/api/collect',{method:'POST',headers:{'X-Daybook-Action':'collect'}});const result=await r.json();if(!r.ok)throw Error(result.error);data=result;adoptPreferences();selected=data.yesterday;render();status('Yesterday’s export is saved and the dashboard is up to date.')}catch(e){status(e.message,true)}finally{b.disabled=false;b.textContent='↓ Collect yesterday'}});
$('#scope').addEventListener('change',()=>{scopeChosen=true;scope=$('#scope').value;selected='';render()});$('#day').addEventListener('change',()=>{selected=$('#day').value;render()});
document.querySelectorAll('[data-range]').forEach(b=>b.addEventListener('click',()=>{range=Number(b.dataset.range);document.querySelectorAll('[data-range]').forEach(x=>x.classList.toggle('selected',x===b));renderTrend()}));
$('#search').addEventListener('input',renderApps);$('#show-all').addEventListener('click',()=>{expanded=!expanded;renderApps()});
$('#csv').addEventListener('click',()=>{const d=current();if(!d)return;const cell=v=>'"'+String(v).replaceAll('"','""')+'"';const safe=v=>/^[=+\-@\t\r]/.test(String(v))?"'"+v:v;const rows=[['date','device_scope','name','reported_seconds','counted_seconds','detail_only','category','exported_rows','completed_day_query'],...apps(d).map(a=>[d.date,scope,safe(a.name),a.seconds,a.counted,a.detail,category(a.name),a.count,d.complete])];const blob=new Blob(['\uFEFF'+rows.map(r=>r.map(cell).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'});const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`daybook-${selected}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)});
load();
setInterval(()=>{if(!document.hidden&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName))load()},60000);
