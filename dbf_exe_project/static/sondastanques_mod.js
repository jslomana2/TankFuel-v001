(function(){
  function num(x){ return Number(String(x).replace(',', '.')); }
  function parsePercent(card){
    const attr = card.getAttribute('data-percent');
    if (attr !== null && attr !== '') return num(attr);
    const b = card.querySelector('.badge');
    if (b){
      const m = b.textContent.match(/(\d+(?:[.,]\d+)?)/);
      if (m) return num(m[1]);
    }
    const fill = card.querySelector('.tank-fill');
    if (fill){
      const m = (fill.getAttribute('style') || '').match(/height:\s*([\d.]+)%/i);
      if (m) return num(m[1]);
    }
    return NaN;
  }
  function statusFor(p){
    if (!(p >= 0)) return {text:'–', color:'var(--muted)', icon:'●'};
    if (p <= 20) return {text:'Bajo',    color:'var(--bad)',  icon:'⚠'};
    if (p <= 50) return {text:'Medio',   color:'var(--warn)', icon:'●'};
    if (p <= 90) return {text:'Alto',    color:'var(--ok)',   icon:'●'};
    return            {text:'Muy alto', color:'var(--very)', icon:'●'};
  }
  function ensureStatusContainer(card){
    let status = card.querySelector('.status');
    if (!status){
      const h3 = card.querySelector('h3') || card.querySelector('.title, header');
      if (h3){
        status = document.createElement('span');
        status.className = 'status';
        status.innerHTML = '<span class="dot"></span><span class="status-text"></span>';
        h3.appendChild(status);
      }
    }
    let dot = status && status.querySelector('.dot');
    if (!dot && status){
      dot = document.createElement('span');
      dot.className = 'dot';
      status.prepend(dot);
    }
    let text = status && status.querySelector('.status-text');
    if (!text && status){
      text = document.createElement('span');
      text.className = 'status-text';
      status.appendChild(text);
    }
    let iconEl = status && status.querySelector('.status-icon');
    return {status, dot, text, iconEl};
  }
  function apply(root){
    const cards = root.querySelectorAll('.card, .tank-card');
    cards.forEach(card => {
      const p = parsePercent(card);
      const s = statusFor(p);
      const {dot, text, iconEl} = ensureStatusContainer(card);
      if (dot)  dot.style.background = s.color;
      if (text) text.textContent = s.text;
      if (iconEl){ iconEl.textContent = s.icon; iconEl.style.color = s.color; }
    });
  }
  const container = document.getElementById('grid-tanques') || document.body;
  apply(document);
  const mo = new MutationObserver(() => apply(document));
  mo.observe(container, {childList:true, subtree:true});
  const refresh = document.getElementById('btn-refresh');
  if (refresh) refresh.addEventListener('click', () => setTimeout(() => apply(document), 0));
})();