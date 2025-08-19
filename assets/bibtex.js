// === 期刊最简缩写（可按你习惯扩充） ===
function abbrJournal(name=''){
  const s = (name||'').toLowerCase().replace(/\./g,'').trim();
  const map = {
    'physical review letters': 'PRL','phys rev lett':'PRL','prl':'PRL',
    'physical review b': 'PRB','phys rev b':'PRB','prb':'PRB',
    'physical review x': 'PRX','phys rev x':'PRX','prx':'PRX',
    'physical review research': 'PRR','phys rev research':'PRR','prr':'PRR',
    'nature physics':'NP','nat phys':'NP',
    'nature communications':'NC','nat commun':'NC','nat comm':'NC',
    'science':'Science','nature':'Nature','chem':'Chem','arxiv':'arXiv'
  };
  for (const k in map){ if (s.includes(k)) return map[k]; }
  const parts = (name||'').split(/[\s-]+/)
    .filter(w=>w.length>=3 && !/^(the|of|and|a|on|in)$/i.test(w));
  return (parts.length?parts.map(w=>w[0]).join(''):'Else').toUpperCase().slice(0,6);
}
function firstAuthorSurname(authors){
  if (!authors||!authors.length) return 'Anon';
  let raw = authors[0]||'';
  if (raw.includes(',')) raw = raw.split(',')[0];
  let sur = raw.trim().split(/\s+/).pop() || raw.trim();
  sur = sur.replace(/[^A-Za-z\u00C0-\u024F\u4E00-\u9FFF]/g,'');
  if (!sur) return 'Anon';
  return /^[A-Za-z]/.test(sur) ? sur[0].toUpperCase()+sur.slice(1).toLowerCase() : sur;
}
function inferYearField(e){
  if (e.year && /^\d{4}$/.test(String(e.year))) return String(e.year);
  const m = (e.date||'').match(/\b(\d{4})\b/);
  return m?m[1]:'0000';
}
function makeBibKey(e){
  const sur = firstAuthorSurname(e.authors||[]);
  const yr  = inferYearField(e);
  const j   = abbrJournal(e.journal || e.booktitle || '');
  return `${sur}${yr}:${j}`;
}
function sanitizeBibVal(v){ return String(v??'').replace(/\r?\n/g,' ').replace(/\s+/g,' ').trim(); }

// ===== 导出：使用自定义 bibkey，并写出 note + rating =====
function toBibTex(e){
  const L = [];
  const type = (e.type||'article');
  const key = makeBibKey(e);
  L.push(`@${type}{${key},`);
  if (e.title) L.push(`  title = {${sanitizeBibVal(e.title)}},`);
  if (e.authors?.length) L.push(`  author = {${e.authors.join(' and ')}},`);
  if (e.journal) L.push(`  journal = {${sanitizeBibVal(e.journal)}},`);
  if (e.booktitle) L.push(`  booktitle = {${sanitizeBibVal(e.booktitle)}},`);
  if (e.year) L.push(`  year = {${e.year}},`);
  if (e.date) L.push(`  date = {${sanitizeBibVal(e.date)}},`);
  if (e.doi)  L.push(`  doi = {${sanitizeBibVal(e.doi)}},`);
  if (e.url)  L.push(`  url = {${sanitizeBibVal(e.url)}},`);
  if (e.arxiv || e.eprint) L.push(`  eprint = {${sanitizeBibVal(e.arxiv||e.eprint)}},`);
  if (e.abstract) L.push(`  abstract = {${sanitizeBibVal(e.abstract)}},`);
  if (e.note) L.push(`  note = {${sanitizeBibVal(e.note)}},`);
  if (typeof e.rating === 'number') L.push(`  rating = {${(+e.rating).toFixed(1)}},`);
  L.push('}');
  return L.join('\n');
}

// ===== 导入：健壮解析花括号/引号/逗号，兼容字段，识别 note + rating =====
function parseBibTex(text){
  const items = [];
  const re = /@(\w+)\s*\{\s*([^,]+)\s*,([\s\S]*?)\}\s*(?=@|$)/gmi;
  let m;
  while ((m = re.exec(text))){
    const type = m[1].trim().toLowerCase();
    const id   = m[2].trim();
    const body = m[3];

    // —— 分割 k=v（考虑花括号/引号嵌套）
    const parts = [];
    let buf = '', depth = 0, inQuote = false;
    for (let i = 0; i < body.length; i++){
      const ch = body[i];
      if (ch === '"') inQuote = !inQuote;
      if (!inQuote){
        if (ch === '{') depth++;
        else if (ch === '}' && depth > 0) depth--;
      }
      if (ch === ',' && depth === 0 && !inQuote){ parts.push(buf); buf=''; }
      else buf += ch;
    }
    if (buf.trim()) parts.push(buf);

    // —— 这里定义 fields，只在本次条目作用域里使用
    const fields = {};
    for (const line of parts){
      const mm = line.match(/^\s*([A-Za-z0-9_-]+)\s*=\s*(.+)\s*$/);
      if (!mm) continue;
      let key = mm[1].toLowerCase();
      let val = mm[2].trim();
      if ((val.startsWith('{') && val.endsWith('}')) || (val.startsWith('"') && val.endsWith('"'))){
        val = val.slice(1,-1);
      }
      fields[key] = val;
    }

    // —— 规范化 arXiv / DOI（供去重）
    const arxivRaw = fields.eprint || fields.arxiv || '';
    const arxivId  = String(arxivRaw).trim().replace(/^arxiv:/i,'').replace(/v\d+$/i,'');
    const doiNorm  = (fields.doi || '').trim().toLowerCase();

    const e = {
      id, type,
      title: fields.title || '',
      authors: fields.author ? fields.author.split(/\s+and\s+/i).map(s=>s.trim()).filter(Boolean) : [],
      journal: fields.journal || '',
      booktitle: fields.booktitle || '',
      year: fields.year ? parseInt(fields.year,10) : undefined,
      date: fields.date || fields.year || '',
      doi: doiNorm,
      url: fields.url || '',
      arxiv: arxivRaw,
      arxivId,
      abstract: fields.abstract || '',
      note: fields.note || '',
      category: 'unsorted',
      rating: 0
    };
    if (fields.rating != null && String(fields.rating).trim() !== ''){
      const r = parseFloat(String(fields.rating));
      if (!Number.isNaN(r)){ e.rating = r; e.manualRating = true; }
    }
    if (!e.journal && e.booktitle) e.journal = e.booktitle;

    items.push(e);
  }
  return items;
}


window.parseBibTex = parseBibTex;
window.toBibTex    = toBibTex;
window._bibAbbr    = { abbrJournal, makeBibKey }; // 可选：调试用

