// Minimal-yet-complete BibLab app logic (import/export/search/sort/drag/board/notes/rating/theme)
const $ = (sel, el=document) => el.querySelector(sel);
const $$ = (sel, el=document) => Array.from(el.querySelectorAll(sel));

// ---- State ----
let entries = [];     // Entry[]
let categories = [];  // {id,name,color}[] - include "Unsorted"
let settings = { theme: 'dark', sort: 'date_desc', view: 'unsorted' };

const LS_KEYS = {
  entries: 'biblab_entries_v42',
  categories: 'biblab_categories_v42',
  settings: 'biblab_settings_v42',
};

// ---- Utils ----
const now = () => Date.now();
const uid = (p='id') => p + '_' + Math.random().toString(36).slice(2,8);
const clamp = (x,a,b) => Math.max(a, Math.min(b, x));

function parseDateGuess(e) {
  // prefer e.date like 'YYYY-MM-DD' or e.year
  if (e.date) {
    const t = Date.parse(e.date);
    if (!isNaN(t)) return t;
  }
  if (e.year) {
    const t = Date.parse(e.year.toString());
    if (!isNaN(t)) return t;
  }
  return 0;
}

function journalTone(j) {
  if (!j) return 'Else';
  const s = j.toLowerCase();
  if (s.includes('phys. rev. lett') || s.includes('prl')) return 'PRL';
  if (s.includes('phys. rev. b') || s === 'prb') return 'PRB';
  if (s.includes('phys. rev. x')) return 'PRX';
  if (s.includes('phys. rev. research') || s.includes('prr')) return 'PRR';
  if (s.includes('nature physics')) return 'NP';
  if (s.includes('nature communications')) return 'NC';
  if (s === 'nature' || s.includes('nature ')) return 'Nature';
  if (s.includes('science')) return 'Science';
  if (s.includes('chem')) return 'Chem';
  if (s.includes('arxiv')) return 'arXiv';
  return 'Else';
}

// ---- Local storage ----
function saveAll() {
  localStorage.setItem(LS_KEYS.entries, JSON.stringify(entries));
  localStorage.setItem(LS_KEYS.categories, JSON.stringify(categories));
  localStorage.setItem(LS_KEYS.settings, JSON.stringify(settings));
}

function loadAll() {
  try {
    entries = JSON.parse(localStorage.getItem(LS_KEYS.entries) || '[]');
    categories = JSON.parse(localStorage.getItem(LS_KEYS.categories) || '[]');
    settings = Object.assign(settings, JSON.parse(localStorage.getItem(LS_KEYS.settings) || '{}'));
  } catch(e){}
  if (!categories.length) categories = [{id:'unsorted', name:'Unsorted', color:'#6ab0ff'}];
}

// ---- Rendering ----
const elCards = $('#cards');
const elBoard = $('#board');
const elCats = $('#category-list');
const tplCard = $('#tpl-card');
const tplCat = $('#tpl-category-item');
const tplCol = $('#tpl-board-column');
const elLog = $('#log');

function setTheme(theme) {
  if (theme === 'light') document.body.classList.add('theme-light');
  else document.body.classList.remove('theme-light');
  $('#btn-theme').textContent = theme === 'light' ? '☀️ 浅色' : '🌙 深色';
}

function applySearchAndSort(list) {
  const q = ($('#q').value || '').trim().toLowerCase();
  const sort = $('#sort').value;
  let arr = list;
  if (q) {
    arr = arr.filter(e => {
      const inStr = (x) => (x||'').toString().toLowerCase().includes(q);
      return inStr(e.title) || inStr((e.authors||[]).join(', ')) || inStr(e.journal) ||
             inStr(e.doi) || inStr(e.abstract) || inStr(e.url);
    });
  }
  const byTitle = (a,b) => (a.title||'').localeCompare(b.title||'');
  const byDate = (a,b) => parseDateGuess(b) - parseDateGuess(a);
  if (sort === 'date_desc') arr.sort(byDate);
  if (sort === 'date_asc') arr.sort((a,b)=>-byDate(a,b));
  if (sort === 'title_asc') arr.sort(byTitle);
  if (sort === 'title_desc') arr.sort((a,b)=>-byTitle(a,b));
  return arr;
}

function renderCategories() {
  const wrap = $('#category-list');
  // Clear previous cat items (except toolbar)
  wrap.querySelectorAll('.cat-item').forEach(n => n.remove());
  categories.forEach(cat => {
    const n = tplCat.content.firstElementChild.cloneNode(true);
    n.dataset.cid = cat.id;
    n.querySelector('.dropzone').dataset.cid = cat.id;
    n.querySelector('.cat-name').textContent = cat.name;
    n.querySelector('.dot').style.background = cat.color || 'var(--accent)';
    const count = entries.filter(e => (e.category || 'unsorted') === cat.id).length;
    n.querySelector('.count').textContent = count;
    // actions
    n.querySelector('.enter').addEventListener('click', () => {
      settings.view = 'unsorted';
      saveAll();
      // filter by this category in cards view
      showCards(cat.id);
    });
    n.querySelector('.exp').addEventListener('click', () => {
      const list = entries.filter(e => (e.category||'unsorted') === cat.id);
      exportBib(list);
    });
    n.querySelector('.clr').addEventListener('click', () => {
      entries.forEach(e => { if ((e.category||'unsorted') === cat.id) e.category = 'unsorted'; });
      saveAll(); renderAll();
    });
    // rename
    n.querySelector('.cat-name').addEventListener('input', (ev)=>{
      cat.name = ev.target.textContent.trim() || cat.name;
      saveAll();
    });
    // dnd
    installDropzone(n.querySelector('.dropzone'));
    wrap.appendChild(n);
  });
}

function installDropzone(zone) {
  zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('over'));
  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('over');
    const id = e.dataTransfer.getData('text/id');
    const entry = entries.find(x => x.id === id);
    if (!entry) return;
    entry.category = zone.dataset.cid || 'unsorted';
    saveAll();
    // accept anim
    zone.classList.add('accept'); setTimeout(()=>zone.classList.remove('accept'), 600);
    renderAll();
  });
}

function makeCard(entry) {
  const n = tplCard.content.firstElementChild.cloneNode(true);
  n.dataset.id = entry.id;
  // tone
  const tone = 'tone-' + journalTone(entry.journal);
  n.classList.add(tone);
  // badges
  n.querySelector('.badge.journal').classList.add('j-' + journalTone(entry.journal));
  n.querySelector('.badge.journal').textContent = entry.journal || '';
  n.querySelector('.badge.type').textContent = (entry.type||'').toUpperCase() || 'ARTICLE';
  if (entry.category && entry.category !== 'unsorted') {
    const cat = categories.find(c => c.id === entry.category);
    const bc = n.querySelector('.badge.category');
    bc.hidden = false;
    bc.textContent = cat ? cat.name : entry.category;
  }
  // title
  n.querySelector('.title').textContent = entry.title || '(无标题)';
  // meta
  n.querySelector('.authors').textContent = (entry.authors||[]).join(', ');
  n.querySelector('.journal-name').textContent = entry.journal || '';
  const dt = entry.date || (entry.year ? String(entry.year) : '');
  n.querySelector('.date').textContent = dt;
  // abstract
  n.querySelector('.abstract').textContent = entry.abstract || '';
  // links
  const lnk = n.querySelectorAll('.links a');
  const [lnPage, lnDoi, lnArxiv] = lnk;
  if (entry.url) { lnPage.href = entry.url; } else { lnPage.style.display='none'; }
  if (entry.doi) { lnDoi.href = 'https://doi.org/' + entry.doi; } else { lnDoi.style.display='none'; }
  if (entry.arxiv || entry.eprint) { lnArxiv.href = 'https://arxiv.org/abs/' + (entry.arxiv || entry.eprint); } else { lnArxiv.style.display='none'; }
  // note
  const note = n.querySelector('.note');
  const noteBadge = n.querySelector('.note-indicator');
  if (entry.note && entry.note.trim().length) {
    note.value = entry.note; noteBadge.hidden = false;
  }
  n.querySelector('.note-toggle').addEventListener('click', () => {
    const blk = n.querySelector('.note-block');
    blk.hidden = !blk.hidden;
  });
  note.addEventListener('input', () => {
    entry.note = note.value;
    noteBadge.hidden = !(entry.note && entry.note.trim().length);
    // auto star
    const auto = Math.min(5, Math.floor((entry.note||'').trim().length / 50) * 0.5);
    if (!entry.manualRating) {
      entry.rating = auto;
      applyStar(n, entry.rating);
    }
    saveAll();
  });
  // rating
  const ratingEl = n.querySelector('.rating');
  ratingEl.addEventListener('click', (e) => {
    const rect = ratingEl.getBoundingClientRect();
    const rel = clamp((e.clientX - rect.left)/rect.width, 0, 1);
    const r = Math.round(rel * 10) / 2; // steps of 0.5
    entry.rating = r;
    entry.manualRating = true;
    applyStar(n, r);
    saveAll();
  });
  applyStar(n, entry.rating || 0);
  // drag
  n.addEventListener('dragstart', (e) => {
    n.classList.add('dragging');
    e.dataTransfer.setData('text/id', entry.id);
  });
  n.addEventListener('dragend', () => n.classList.remove('dragging'));
  return n;
}

function applyStar(card, rating) {
  const fg = card.querySelector('.stars-fg');
  const txt = card.querySelector('.stars-text');
  const w = clamp(rating/5, 0, 1) * 110;
  fg.style.width = w + 'px';
  //txt.textContent = (rating||0).toFixed(1);
}

function showCards(catId=null) {
  settings.view = 'unsorted';
  $('#board').hidden = true;
  $('#cards').hidden = false;
  const list = catId ? entries.filter(e => (e.category||'unsorted') === catId) : entries;
  renderCards(applySearchAndSort(list));
}

function renderCards(list) {
  elCards.innerHTML = '';
  list.forEach(e => elCards.appendChild(makeCard(e)));
}

function showBoard() {
  settings.view = 'board';
  $('#cards').hidden = true;
  $('#board').hidden = false;
  renderBoard();
}

function renderBoard() {
  elBoard.innerHTML = '';
  // columns by categories (keep order)
  categories.forEach(cat => {
    const col = tplCol.content.firstElementChild.cloneNode(true);
    col.dataset.cid = cat.id;
    col.querySelector('.name').textContent = cat.name;
    col.querySelector('.dot').style.background = cat.color || 'var(--ok)';
    const dz = col.querySelector('.dropzone');
    dz.dataset.cid = cat.id;
    installDropzone(dz);
    const list = entries.filter(e => (e.category||'unsorted') === cat.id);
    col.querySelector('.count').textContent = list.length;
    col.querySelector('.exp').addEventListener('click', () => exportBib(list));
    // add cards (compact tiles by CSS)
    applySearchAndSort(list).forEach(e => dz.appendChild(makeCard(e)));
    elBoard.appendChild(col);
  });
}

function renderAll() {
  renderCategories();
  if (settings.view === 'board') showBoard();
  else showCards();
}

// ---- Import / Export ----
async function importBibFile(file) {
  const text = await file.text();
  const parsed = parseBibTex(text); // from bibtex.js
  const nowt = now();
  parsed.forEach(p => {
    p.id = p.id || uid('ref');
    p.category = p.category || 'unsorted';
    p.createdAt = nowt; p.updatedAt = nowt;
  });
  entries = entries.concat(parsed);
  saveAll(); renderAll();
  log(`导入 BibTeX 条目：${parsed.length} 篇`);
}

async function importJSONFile(file) {
  const text = await file.text();
  const data = JSON.parse(text);
  entries = data.entries || data.items || [];
  categories = data.categories || [{id:'unsorted', name:'Unsorted', color:'#6ab0ff'}];
  settings = Object.assign(settings, data.settings || {});
  saveAll(); renderAll();
  log(`导入快照成功：${entries.length} 篇，分类 ${categories.length} 个`);
}

function exportSnapshot() {
  const data = { entries, categories, settings };
  const blob = new Blob([JSON.stringify(data, null, 2)], {type:'application/json'});
  downloadBlob(blob, `biblab_snapshot_${new Date().toISOString().slice(0,10)}.json`);
}

// 假设你已有 exportBib(list) —— 在里面加入这一段
function exportBib(list){
  const arr = list || applySearchAndSort(entries);
  const used = new Map();  // key -> 次数（用于 a,b,c 后缀）
  const out = arr.map(e => {
    // 先用 bibtex.js 的 toBibTex 生成字符串，再把首行的 key 拿出来检查
    const s = toBibTex(e);
    const m = s.match(/^@\w+\{([^,]+),/m);
    if (!m) return s;
    let key = m[1];
    if (used.has(key)){
      const n = used.get(key) + 1;
      used.set(key, n);
      const suffix = String.fromCharCode('a'.charCodeAt(0) + (n-1)); // a,b,c...
      const newKey = key + suffix;
      return s.replace(/^(@\w+\{)[^,]+,/, `$1${newKey},`);
    }else{
      used.set(key, 0);
      return s;
    }
  }).join("\n\n");

  const blob = new Blob([out], {type:'text/plain;charset=utf-8'});
  downloadBlob(blob, `export_${arr.length}_items.bib`);
}


function downloadBlob(blob, name) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  setTimeout(()=>URL.revokeObjectURL(a.href), 1000);
}

// ---- Logging ----
function log(msg) { if (elLog) elLog.textContent = msg; }

// ---- Event wiring ----
function wire() {
  $('#file-bib')?.addEventListener('change', (e)=>{
    const f = e.target.files[0]; if (f) importBibFile(f);
    e.target.value = '';
  });
  $('#file-json')?.addEventListener('change', (e)=>{
    const f = e.target.files[0]; if (f) importJSONFile(f);
    e.target.value = '';
  });
  $('#btn-export-json')?.addEventListener('click', exportSnapshot);
  $('#btn-export-bib')?.addEventListener('click', ()=> exportBib(applySearchAndSort(entries)));
  $('#q')?.addEventListener('input', ()=> renderAll());
  $('#sort')?.addEventListener('change', ()=> renderAll());
  $('#btn-unsorted')?.addEventListener('click', ()=> { settings.view='unsorted'; renderAll(); });
  $('#btn-board')?.addEventListener('click', ()=> { settings.view='board'; renderAll(); });
  $('#btn-clear')?.addEventListener('click', ()=> {
    if (confirm('确定要清空本地数据吗？此操作不可撤销。')) {
      localStorage.removeItem(LS_KEYS.entries);
      localStorage.removeItem(LS_KEYS.categories);
      localStorage.removeItem(LS_KEYS.settings);
      entries = []; categories = [{id:'unsorted', name:'Unsorted', color:'#6ab0ff'}]; settings = { theme: settings.theme, sort: 'date_desc', view:'unsorted' };
      renderAll();
      log('已清空本地数据。');
    }
  });
  $('#btn-theme')?.addEventListener('click', ()=>{
    settings.theme = (settings.theme === 'light' ? 'dark' : 'light');
    setTheme(settings.theme); saveAll();
  });

  // add category
  $('#btn-add-cat')?.addEventListener('click', ()=>{
    const c = { id: uid('cat'), name: 'New Category', color: randomPastel() };
    categories.push(c); saveAll(); renderAll();
  });

  // allow dropping .bib onto whole page
  document.addEventListener('dragover', e => e.preventDefault());
  document.addEventListener('drop', async (e) => {
    if (!e.dataTransfer || !e.dataTransfer.files?.length) return;
    e.preventDefault();
    for (const f of e.dataTransfer.files) {
      if (/\.(bib|txt)$/i.test(f.name)) await importBibFile(f);
      else if (/\.json$/i.test(f.name)) await importJSONFile(f);
    }
  });
}

function randomPastel() {
  const h = Math.floor(Math.random()*360);
  return `hsl(${h}deg, 70%, 75%)`;
}

// ---- Startup ----
loadAll();
document.addEventListener('DOMContentLoaded', () => {
  setTheme(settings.theme);
  // initial categories if none
  if (!categories.length) categories = [{id:'unsorted', name:'Unsorted', color:'#6ab0ff'}];
  renderAll();
  wire();
});


