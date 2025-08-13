const $ = (sel, el=document) => el.querySelector(sel);
const $$ = (sel, el=document) => [...el.querySelectorAll(sel)];
const isAbs = u => /^https?:\/\//i.test(u||"");

// Organic chemistry journals
const LEGEND = [
  ["JACS","J. Am. Chem. Soc."],
  ["Angew","Angew. Chem. Int. Ed."],
  ["ChemEurJ","Chem. Eur. J."],
  ["EJOC","Eur. J. Org. Chem."],
  ["AdvSynthCatal","Adv. Synth. Catal."],
  ["OBC","Org. Biomol. Chem."],
  ["OrgChemFront","Org. Chem. Frontiers"],
  ["Tetrahedron","Tetrahedron"],
  ["TetLett","Tetrahedron Letters"],
  ["BJOC","Beilstein J. Org. Chem."],
  ["NChem","Nature Chemistry"],
  ["ChemSci","Chemical Science"]
];

let ALL_ITEMS = [];
let SERVER_WINDOW = 3;

const cssVarName = (k)=> (k||"").toLowerCase();

function safeApplyLegend(){
  const el = $("#legend"); if(!el) return;
  el.innerHTML = LEGEND.map(([k,v]) =>
    `<span class="legend-item"><span class="swatch" style="background: var(--c-${cssVarName(k)});"></span>${v}</span>`
  ).join("");
}

function safeMakeSourceSelect(){
  const sel = $("#src"); if(!sel) return;
  sel.innerHTML = `<option value="">全部来源</option>` +
    LEGEND.map(([k,v])=>`<option value="${k}">${v}</option>`).join("");
}

function fmtAuthorsList(authors){
  if(!authors || !authors.length) return [];
  return authors.map(a => typeof a === 'string' ? a : (a.name || `${a.given||''} ${a.family||''}`.trim()));
}
function authorsCondensed(authors){
  const list = fmtAuthorsList(authors);
  const n = list.length;
  if(n === 0) return '';
  if(n <= 3) return list.join(', ');
  return `${list[0]} … ${list[n-1]}（共 ${n} 人）`;
}
function formatDate(iso){
  if(!iso) return ""; const d = new Date(iso);
  const p = n => String(n).padStart(2,'0');
  return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}
function withinDays(iso, days){
  if(days==='all') return true;
  const dt = new Date(iso); const now = new Date();
  return (now - dt)/(1000*60*60*24) <= Number(days)+0.01;
}
function filterByQuery(items, q){
  if(!q) return items;
  const s = q.toLowerCase();
  return items.filter(x =>
    (x.title||'').toLowerCase().includes(s) ||
    (x.journal||'').toLowerCase().includes(s) ||
    (x.doi||'').toLowerCase().includes(s) ||
    (x.summary||'').toLowerCase().includes(s) ||
    (x.authors||[]).join(' ').toLowerCase().includes(s)
  );
}
function normalize(item){
  const uid = `${item.journalKey}|${item.doi||item.arxiv||item.link}|${item.date||''}`;
  return {...item, uid};
}
const bestLink = (it)=>{
  if (isAbs(it.arxiv)) return it.arxiv;
  if (isAbs(it.link))  return it.link;
  if (it.doi)          return `https://doi.org/${it.doi}`;
  return '#';
};

// Favorites manager
const FavStore = {
  keyNew: 'oc_favs_v2',
  _parse(raw){ try{const v=JSON.parse(raw||'[]'); return Array.isArray(v)?v:[];}catch{return []} },
  minify(item){
    const uid=item.uid||`${item.journalKey}|${item.doi||item.arxiv||item.link}|${item.date||''}`;
    return {uid,title:item.title||'',authors:Array.isArray(item.authors)?item.authors.slice(0):[],date:item.date||'',
      journalKey:item.journalKey||'',journalShort:item.journalShort||item.journalKey||'',journal:item.journal||'',
      type:item.type||'',link:item.link||'',arxiv:item.arxiv||'',doi:item.doi||'',summary:item.summary||''};
  },
  load(){ return this._parse(localStorage.getItem(this.keyNew)); },
  save(list){ localStorage.setItem(this.keyNew, JSON.stringify(list)); },
  has(uid){ return this.load().some(x => x.uid===uid); },
  add(item){ const l=this.load(); const m=this.minify(item); if(!l.some(x=>x.uid===m.uid)){ l.push(m); this.save(l);} return l.length; },
  remove(uid){ const l=this.load().filter(x=>x.uid!==uid); this.save(l); return l.length; },
  clear(){ this.save([]); return 0; }
};
function updateFavCount(){ const n=FavStore.load().length; $("#fav-count")&&($("#fav-count").textContent=n); }

function cardFromItem(item){
  const tpl = $("#card-tpl")?.content?.cloneNode(true); if(!tpl) return document.createTextNode('');
  const root  = tpl.querySelector('.card');
  const badge = tpl.querySelector('.badge');
  const type  = tpl.querySelector('.type');
  const time  = tpl.querySelector('.time');
  const title = tpl.querySelector('.title');
  const meta  = tpl.querySelector('.meta');
  const abs   = tpl.querySelector('.abs');
  const links = tpl.querySelector('.links');
  const star  = tpl.querySelector('.star');

  const link = bestLink(item);
  const arxiv = isAbs(item.arxiv) ? item.arxiv : '';
  const pdfLink = arxiv && arxiv.includes('/abs/') ? (arxiv.replace('/abs/','/pdf/') + '.pdf') : '';

  const keyClass = cssVarName(item.journalKey);
  root.classList.add('tone', keyClass);
  badge.classList.add(keyClass);
  badge.textContent = item.journalShort || item.journalKey;
  type.textContent  = item.type==='accepted' ? 'Accepted' : (item.type==='preprint' ? 'Preprint' : 'Published');
  time.textContent  = formatDate(item.date);
  title.innerHTML   = `<a href="${link}" target="_blank" rel="noopener noreferrer nofollow">${item.title}</a>`;

  const authorsLine = authorsCondensed(item.authors);
  meta.innerHTML = `<strong>作者：</strong>${authorsLine}${item.doi?`　·　DOI: ${item.doi}`:''}`;
  abs.innerHTML  = `<strong>摘要：</strong>${item.summary || '（无摘要）'}`;

  links.innerHTML = `
    <a href="${link}" target="_blank" rel="noopener noreferrer nofollow">页面</a>
    ${arxiv?`<a href="${arxiv}" target="_blank" rel="noopener noreferrer nofollow">arXiv</a>`:''}
    ${pdfLink?`<a href="${pdfLink}" target="_blank" rel="noopener noreferrer nofollow">PDF</a>`:''}
  `;

  if (FavStore.has(item.uid)){ star.classList.add('on'); star.textContent='★'; }
  star?.addEventListener('click', ()=>{
    if (FavStore.has(item.uid)){ FavStore.remove(item.uid); star.classList.remove('on'); star.textContent='☆'; }
    else { FavStore.add(item); star.classList.add('on'); star.textContent='★'; }
    updateFavCount();
  });

  return tpl;
}

function readSelections(){
  const src  = $("#src")?.value || "";
  const win  = $("#win")?.value || "3";
  const stat = $("#stat")?.value || "all";
  const url = new URL(location.href);
  const q = url.searchParams.get('q') || '';
  if(q) $('#q') && ($('#q').value = q);
  return {src, win, stat, q};
}

function render(){
  const {src, win, stat, q} = readSelections();
  let items = ALL_ITEMS.slice(0);
  if(src) items = items.filter(it => it.journalKey === src);
  if(stat !== 'all') items = items.filter(it => it.type === stat);
  items = items.filter(it => withinDays(it.date, win));
  items = filterByQuery(items, q);

  const box = $('#cards'); if(!box) return 0;
  box.innerHTML='';
  items.forEach(it=> box.appendChild(cardFromItem(it)) );
  $("#total") && ($("#total").textContent = items.length);
  return items.length;
}

function toBib(item){
  const type = (item.type==='preprint') || (item.arxiv && (!item.doi || item.type==='accepted')) ? 'misc' : 'article';
  const au = fmtAuthorsList(item.authors).join(' and ');
  const key = (fmtAuthorsList(item.authors)[0]||'na') + (item.date? new Date(item.date).getFullYear(): '');
  const lines = [];
  lines.push(`@${type}{${key},`);
  lines.push(`  title={${item.title||''}},`);
  if(au) lines.push(`  author={${au}},`);
  if(item.journal) lines.push(`  journal={${item.journal}},`);
  const y = (item.date? new Date(item.date).getFullYear(): undefined);
  if(y) lines.push(`  year={${y}},`);
  if(item.doi) lines.push(`  doi={${item.doi}},`);
  if(item.arxiv){
    const id = item.arxiv.replace(/^.*\//,''); lines.push(`  eprint={${id}},`); lines.push(`  archivePrefix={arXiv},`);
  }
  lines.push(`  url={${bestLink(item)}},`);
  lines.push('}');
  return lines.join('\n');
}
function exportBib(list){
  if(!list || !list.length){ alert('还没有收藏任何文章'); return; }
  const bib = list.map(toBib).join('\n\n');
  const ts = new Date().toISOString().slice(0,19).replace(/[:T]/g,'-');
  const name = `favorites-${ts}.bib`;
  const blob = new Blob([bib], {type:'text/x-bibtex;charset=utf-8'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = name; document.body.appendChild(a);
  a.click(); setTimeout(()=>{ URL.revokeObjectURL(url); a.remove(); },0);
}

function openFavs(){
  const dlg = $('#fav-dialog'); const box = $("#fav-list");
  if(!dlg || !box){ alert('收藏夹视图未找到'); return; }
  const list = FavStore.load();
  if(!list.length){
    box.innerHTML = '<p class="meta">尚未收藏任何文章。</p>';
  }else{
    box.innerHTML = list.map(item => `
      <article class="card tone ${cssVarName(item.journalKey)}">
        <div class="card-head">
          <span class="badge ${cssVarName(item.journalKey)}">${item.journalShort||item.journalKey}</span>
          <span class="type">${item.type==='accepted'?'Accepted':(item.type==='preprint'?'Preprint':'Published')}</span>
          <span class="time">${formatDate(item.date)}</span>
          <button class="star on" data-uid="${item.uid}">★</button>
        </div>
        <h3 class="title"><a href="${bestLink(item)}" target="_blank" rel="noopener noreferrer nofollow">${item.title}</a></h3>
        <p class="meta"><strong>作者：</strong>${authorsCondensed(item.authors)}${item.doi?`　·　DOI: ${item.doi}`:''}</p>
        ${item.summary?`<p class="abs"><strong>摘要：</strong>${item.summary}</p>`:''}
      </article>`).join("");
    $$(".star", box).forEach(btn=>{
      btn.addEventListener('click', ()=>{
        const uid = btn.dataset.uid; FavStore.remove(uid);
        btn.closest('article').remove(); updateFavCount();
        if (!FavStore.load().length){ box.innerHTML = '<p class="meta">尚未收藏任何文章。</p>'; }
      });
    });
  }
  dlg.showModal();
}

async function load(){
  safeApplyLegend(); safeMakeSourceSelect();
  updateFavCount();

  let json = null;
  try{
    const resp = await fetch('data/articles.json', {cache:'no-store'});
    if(!resp.ok) throw new Error(`HTTP ${resp.status}`);
    json = await resp.json();
  }catch(err){
    const box = $('#cards');
    if(box) box.innerHTML = `<p class="meta">数据读取失败：${String(err)}</p>`;
    console.error('load articles.json failed', err);
    return;
  }

  ALL_ITEMS = (json.items||[]).map(normalize);
  SERVER_WINDOW = json.windowDays || 3;
  if (SERVER_WINDOW > 3 && $("#win")) $("#win").value = 'all';

  const n = render();
  if(n===0 && $("#win") && $("#win").value !== 'all'){ $("#win").value = 'all'; render(); }
}

$('#btn-refresh')?.addEventListener('click', load);
$('#src')?.addEventListener('change', render);
$('#win')?.addEventListener('change', render);
$('#stat')?.addEventListener('change', render);
$('#q')?.addEventListener('keydown', (e)=>{
  if(e.key==='Enter'){
    const v=e.target.value.trim(); const u=new URL(location.href);
    if(v) u.searchParams.set('q',v); else u.searchParams.delete('q');
    location.href = u.toString();
  }
});
$('#btn-favs')?.addEventListener('click', openFavs);
$('#btn-export-bib')?.addEventListener('click', ()=> exportBib(FavStore.load()));
$('#btn-export-bib-2')?.addEventListener('click', ()=> exportBib(FavStore.load()));
$('#btn-clear-favs')?.addEventListener('click', ()=>{ if(confirm('确定清空所有收藏？')){ FavStore.clear(); updateFavCount(); const box=$("#fav-list"); if(box) box.innerHTML='<p class="meta">尚未收藏任何文章。</p>'; }});

load();
