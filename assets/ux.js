// UX extras: board-page toggle + hover preview
document.addEventListener('DOMContentLoaded', () => {
  const body = document.body;
  const btnBoard = document.querySelector('#btn-board');
  const btnUnsorted = document.querySelector('#btn-unsorted');
  const boardEl = document.querySelector('#board');

  function enterBoardPage() { body.classList.add('board-page'); }
  function leaveBoardPage() { body.classList.remove('board-page'); }

  btnBoard?.addEventListener('click', () => setTimeout(() => {
    if (boardEl && !boardEl.hasAttribute('hidden')) enterBoardPage();
  }, 10));

  btnUnsorted?.addEventListener('click', () => leaveBoardPage());

  // Preview panel
  const preview = document.createElement('div');
  preview.id = 'preview-panel';
  preview.style.display = 'none';
  document.body.appendChild(preview);
  let showing = false;

  function showPreviewFor(card, x, y) {
    const clone = card.cloneNode(true);
    clone.classList.remove('dragging');
    preview.innerHTML = ''; preview.appendChild(clone);
    const offset = 16, w = 540, h = 360;
    let left = x + offset, top = y + offset;
    const vw = innerWidth, vh = innerHeight;
    if (left + w > vw) left = Math.max(12, vw - w - 12);
    if (top + h > vh) top = Math.max(12, vh - h - 12);
    preview.style.left = left + 'px'; preview.style.top = top + 'px';
    preview.style.display = 'block'; showing = true;
  }
  function hidePreview(){ preview.style.display = 'none'; preview.innerHTML = ''; showing = false; }

  document.addEventListener('mousemove', (e) => {
    if (!showing) return;
    const offset = 16, w = 540, h = 360;
    let left = e.clientX + offset, top = e.clientY + offset;
    const vw = innerWidth, vh = innerHeight;
    if (left + w > vw) left = Math.max(12, vw - w - 12);
    if (top + h > vh) top = Math.max(12, vh - h - 12);
    preview.style.left = left + 'px'; preview.style.top = top + 'px';
  });

  document.addEventListener('mouseenter', (e) => {
    const target = e.target;
    if (!(target instanceof Element)) return;
    const card = target.closest?.('.board .card');
    if (card) showPreviewFor(card, e.clientX || 80, e.clientY || 80);
  }, true);
  document.addEventListener('mouseleave', (e) => {
    const target = e.target;
    if (!(target instanceof Element)) return;
    if (target.closest?.('.board .card')) hidePreview();
  }, true);
  boardEl?.addEventListener('mouseleave', hidePreview);
  boardEl?.addEventListener('scroll', hidePreview, true);
});
