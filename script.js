// スクロールでヘッダーに影をつける
const header = document.querySelector('.site-header');

const updateHeader = () => {
  header.classList.toggle('scrolled', window.scrollY > 20);
};

window.addEventListener('scroll', updateHeader, { passive: true });
updateHeader();

// ------------------------------------------------------------------
// 日本語を文節の切れ目で折り返す（2026-09-14）
// CSS の word-break:auto-phrase は Chrome だけが対応で、iPhone（Safari・iPhone版Chrome）
// では単語の途中で折れていた（例：フ／ローリング）。Chrome が中で使っているのと同じ
// BudouX で、どのブラウザでも文節の切れ目に折り返し位置（<wbr>）を入れる。
// ------------------------------------------------------------------
(function () {
  if (!window.BudouxJa) return;
  const parser = new window.BudouxJa.Parser(window.BudouxJa.model, {
    separator: document.createElement('wbr')
  });
  const SEL = 'p, li, dd, dt, h1, h2, h3, figcaption, th, td, .lead-sub, .checktime-note, .checktime-label';
  // 行末に残してはいけない字（開きかっこ）／行頭に来てはいけない字
  const OPEN = '（「『【〈〔［';
  const CLOSE = '、。，．）」』】〉〕］！？ー／・ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮ：；';

  const prevChar = (node) => {
    for (let n = node.previousSibling; n; n = n.previousSibling) {
      const t = n.textContent; if (t) return t[t.length - 1];
    }
    return '';
  };
  const nextChar = (node) => {
    for (let n = node.nextSibling; n; n = n.nextSibling) {
      const t = n.textContent; if (t) return t[0];
    }
    return '';
  };

  // 文字の種類で「ここは折ってよい」を足す：開きかっこの前、句読点・閉じかっこ・「・」「／」の後ろ
  const BEFORE = /[（「『【〈〔［]/;
  const AFTER = /[、。，．）」』】〉〕］！？・／]/;
  const addOpportunities = (el) => {
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    const nodes = [];
    for (let n; (n = walker.nextNode());) {
      if (n.parentElement.closest('.nb')) continue;
      if (BEFORE.test(n.data) || AFTER.test(n.data)) nodes.push(n);
    }
    nodes.forEach((n) => {
      const s = n.data;
      const frag = document.createDocumentFragment();
      let buf = '';
      for (let i = 0; i < s.length; i++) {
        const ch = s[i];
        if (BEFORE.test(ch) && buf) { frag.appendChild(document.createTextNode(buf)); frag.appendChild(document.createElement('wbr')); buf = ''; }
        buf += ch;
        if (AFTER.test(ch) && i < s.length - 1) { frag.appendChild(document.createTextNode(buf)); frag.appendChild(document.createElement('wbr')); buf = ''; }
      }
      if (buf) frag.appendChild(document.createTextNode(buf));
      n.parentNode.replaceChild(frag, n);
    });
  };


  // 開きかっこと次の1文字を「くっつける」。Safari（少なくとも検証に使ったWebKit）は
  // 行末に「（」を残して折ることがあるため、かっこの直後では折れないようにしておく
  const glueOpen = (el) => {
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    const nodes = [];
    for (let n; (n = walker.nextNode());) {
      if (n.parentElement.closest('.nb, .glue')) continue;
      if (/[（「『【〈〔［]./.test(n.data)) nodes.push(n);
    }
    nodes.forEach((n) => {
      const s = n.data, frag = document.createDocumentFragment();
      let last = 0;
      s.replace(/[（「『【〈〔［]+./g, (m, idx) => {
        if (idx > last) frag.appendChild(document.createTextNode(s.slice(last, idx)));
        const sp = document.createElement('span');
        sp.className = 'glue'; sp.style.whiteSpace = 'nowrap'; sp.textContent = m;
        frag.appendChild(sp); last = idx + m.length; return m;
      });
      if (last < s.length) frag.appendChild(document.createTextNode(s.slice(last)));
      n.parentNode.replaceChild(frag, n);
    });
  };

  document.querySelectorAll(SEL).forEach((el) => {
    if (el.parentElement && el.parentElement.closest(SEL)) return;
    if (el.closest('.hero, .hero2, .hero-pdf, #gate')) return;
    parser.applyToElement(el);
    addOpportunities(el);
    glueOpen(el);
    // 禁則：開きかっこの直後・句読点や閉じかっこの直前の折り返し位置は消す。
    // .nb（電話番号・価格・固有名詞）の中の折り返し位置も消す
    el.querySelectorAll('wbr').forEach((w) => {
      if (w.closest('.nb') || OPEN.includes(prevChar(w)) || CLOSE.includes(nextChar(w))) w.remove();
    });
  });
})();

// ------------------------------------------------------------------
// メニュー（2026-09-23）右上のボタンで全画面のメニューを開閉する
// ------------------------------------------------------------------
(function () {
  var btn = document.getElementById('menuBtn');
  var panel = document.getElementById('menuPanel');
  var closeBtn = document.getElementById('menuClose');
  if (!btn || !panel) return;

  function open() {
    panel.hidden = false;
    document.body.classList.add('menu-open');
    btn.setAttribute('aria-expanded', 'true');
    (panel.querySelector('a') || closeBtn).focus({ preventScroll: true });
  }
  function close(giveBackFocus) {
    panel.hidden = true;
    document.body.classList.remove('menu-open');
    btn.setAttribute('aria-expanded', 'false');
    if (giveBackFocus !== false) btn.focus({ preventScroll: true });
  }

  btn.addEventListener('click', open);
  if (closeBtn) closeBtn.addEventListener('click', function () { close(); });
  // 行き先を押したら閉じる（同じページの中の移動なので）
  panel.querySelectorAll('a[href^="#"]').forEach(function (a) {
    a.addEventListener('click', function () { close(false); });
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !panel.hidden) close();
  });
  // 画面が広くなったら閉じる（ヘッダーの並びに戻るため）
  window.addEventListener('resize', function () {
    if (!panel.hidden && window.innerWidth > 1024) close(false);
  });
})();
