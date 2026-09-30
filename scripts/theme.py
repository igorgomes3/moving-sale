#!/usr/bin/env python3
"""
Camada de apresentacao PUBLICA do Moving Sale.

Design gerado no Google Stitch (projeto "Moving Sale - Desapego Marketplace",
design system "Authentic Classifieds & Moving Sale"): estrutura de
classificados que o usuario brasileiro ja reconhece — busca no topo, chips de
categoria, sidebar de filtros, grid de cards com preco em destaque e botao
"Ver detalhes".

REGRA DE OURO desta camada (pedido explicito do Igor, 26/09):
  - A pagina publica NUNCA expoe dado financeiro: nem total arrecadado, nem
    taxas, nem preco de item VENDIDO, nem plataforma de venda, nem disputa.
  - Item vendido aparece desaturado com selo "Vendido" e SEM preco.
  - Sem tachado, sem desconto, sem contagem regressiva, sem copy apelativa.
  - Nada disso aparece aqui; so no /admin.html (uso privado do Igor).

Este modulo nao importa nada de build.py — recebe os dados prontos. Assim a
logica financeira (calc.py, fees, totais) fica separada da apresentacao.
"""
from __future__ import annotations

import html
import json
import re
from urllib.parse import quote

# ------------------------------------------------------------------ tokens

BRAND = "Desapego"

CATEGORY_ORDER = [
    "Eletrodoméstico", "Móvel", "Eletrônico", "Vestuário", "Livro", "Games",
]


def brl(value) -> str:
    if value is None:
        return "—"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def esc(text) -> str:
    return html.escape(str(text if text is not None else ""), quote=True)


def public_price(item: dict) -> str | None:
    """Preco a exibir publicamente. None = item vendido, sem preco."""
    if item.get("status") == "vendido":
        return None
    p = item.get("asking_price")
    if p is None:
        return "Preço a combinar"
    return brl(p)


# ------------------------------------------------------------------ CSS

CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#f7f7f8;--card:#fff;--line:#e5e7eb;--line2:#f0f0f2;
  --txt:#111827;--dim:#6b7280;--dim2:#9ca3af;
  --accent:#e8590c;--accent-soft:#fff4ec;--accent-line:#ffd9bf;
  --sold-bg:#f3f4f6;--sold-txt:#6b7280;
  --r:10px;--shadow:0 1px 2px rgba(17,24,39,.04);
  --shadow-hi:0 6px 20px rgba(17,24,39,.10);
}
html{-webkit-text-size-adjust:100%}
body{background:var(--bg);color:var(--txt);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Inter","Segoe UI",Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased;min-height:100vh;display:flex;flex-direction:column}
.wrap{max-width:1280px;margin:0 auto;padding:0 20px;width:100%}
footer.site{margin-top:auto}
a{color:inherit}
img{max-width:100%}
.wrap{max-width:1280px;margin:0 auto;padding:0 20px}

/* ---------- top bar ---------- */
.topbar{background:var(--card);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:20}
.topbar .inner{max-width:1280px;margin:0 auto;padding:12px 20px;display:flex;align-items:center;gap:16px}
.brand{font-size:19px;font-weight:750;letter-spacing:-.02em;text-decoration:none;white-space:nowrap}
.brand span{color:var(--accent)}
.searchbox{flex:1;display:flex;align-items:center;gap:0;background:var(--bg);border:1px solid var(--line);border-radius:999px;padding:0 6px 0 16px;max-width:640px;margin:0 auto;transition:.15s}
.searchbox:focus-within{border-color:var(--accent);background:var(--card);box-shadow:0 0 0 3px var(--accent-soft)}
.searchbox input{flex:1;border:none;background:transparent;font:inherit;font-size:15px;padding:10px 0;color:var(--txt)}
.searchbox input:focus{outline:none}
.searchbox input::placeholder{color:var(--dim2)}
.searchbox button{border:none;background:transparent;color:var(--dim);font-size:15px;padding:8px 12px;cursor:pointer;border-radius:999px}
.searchbox button:hover{color:var(--accent)}
.locchip{display:flex;align-items:center;gap:6px;font-size:13.5px;color:var(--dim);white-space:nowrap;background:var(--bg);border:1px solid var(--line);border-radius:999px;padding:7px 13px}

/* ---------- categorias ---------- */
.catbar{background:var(--card);border-bottom:1px solid var(--line)}
.catbar .inner{max-width:1280px;margin:0 auto;padding:0 20px;display:flex;gap:6px;overflow-x:auto;scrollbar-width:none}
.catbar .inner::-webkit-scrollbar{display:none}
.catbar button{background:none;border:none;border-bottom:2px solid transparent;color:var(--dim);font:inherit;font-size:14px;font-weight:600;padding:12px 11px;cursor:pointer;white-space:nowrap;transition:.15s}
.catbar button:hover{color:var(--txt)}
.catbar button[aria-pressed="true"]{color:var(--accent);border-bottom-color:var(--accent)}

/* ---------- layout 2 colunas ---------- */
.shell{display:grid;grid-template-columns:224px 1fr;gap:26px;align-items:start;padding:24px 0 70px;flex:1}
aside{position:sticky;top:132px}
.fgroup{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:15px 16px;margin-bottom:14px;box-shadow:var(--shadow)}
.fgroup h3{font-size:12px;text-transform:uppercase;letter-spacing:.07em;color:var(--dim);font-weight:700;margin-bottom:11px}
.fgroup label{display:flex;align-items:center;gap:9px;font-size:14px;padding:6px 0;cursor:pointer;color:var(--txt)}
.fgroup input[type=checkbox],.fgroup input[type=radio]{accent-color:var(--accent);width:16px;height:16px;cursor:pointer}
.fclear{width:100%;background:none;border:1px solid var(--line);border-radius:8px;color:var(--txt);font:inherit;font-size:13.5px;font-weight:600;padding:9px;cursor:pointer}
.fclear:hover{color:var(--accent);border-color:var(--accent-line);background:var(--accent-soft)}
.fgroup select{width:100%;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--txt);font:inherit;font-size:14px;padding:9px 10px;cursor:pointer;appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath fill='%236b7280' d='M6 8 0 2l1.4-1.4L6 5.2 10.6.6 12 2z'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 11px center}
.fgroup select:focus{outline:none;border-color:var(--accent)}

/* ---------- cabeçalho de resultados ---------- */
.results-head{display:flex;align-items:baseline;justify-content:space-between;gap:14px;margin-bottom:16px;flex-wrap:wrap}
.results-head h1{font-size:20px;font-weight:700;letter-spacing:-.01em}
.results-head .n{color:var(--dim);font-size:14px}

/* ---------- grid + card ---------- */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(232px,1fr));gap:18px}
.card{position:relative;background:var(--card);border:1px solid var(--line);border-radius:var(--r);overflow:hidden;display:flex;flex-direction:column;text-decoration:none;color:inherit;box-shadow:var(--shadow);transition:transform .16s ease,box-shadow .16s ease,border-color .16s}
.card:hover{transform:translateY(-3px);box-shadow:var(--shadow-hi);border-color:#d6d8dd}
.ph{position:relative;aspect-ratio:4/3;background:linear-gradient(135deg,#e9eaed,#dfe1e5);display:flex;align-items:center;justify-content:center;overflow:hidden}
.ph img{width:100%;height:100%;object-fit:cover;display:block}
.nofoto{color:#8b93a0;font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase}
.badge{position:absolute;top:9px;left:9px;font-size:10.5px;font-weight:750;letter-spacing:.06em;text-transform:uppercase;padding:4px 9px;border-radius:6px;background:rgba(255,255,255,.94);color:var(--dim);box-shadow:0 1px 3px rgba(17,24,39,.12)}
.badge.b-sold{background:rgba(17,24,39,.82);color:#fff}
.body{padding:12px 13px 13px;display:flex;flex-direction:column;gap:5px;flex:1}
.cat{font-size:11.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--dim2)}
.name{font-size:14.5px;font-weight:650;line-height:1.34;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.cond{font-size:12.5px;color:var(--dim)}
.price{margin-top:auto;padding-top:9px;display:flex;align-items:baseline;gap:7px;flex-wrap:wrap}
.price .now{font-size:20px;font-weight:750;letter-spacing:-.02em;color:var(--accent)}
.price .undef{font-size:15px;font-weight:650;color:var(--dim)}
.price .lbl{font-size:11.5px;color:var(--dim2)}
.card .cta{display:block;text-align:center;margin-top:9px;padding:9px;border:1px solid var(--accent-line);border-radius:8px;font-size:13.5px;font-weight:700;color:var(--accent);background:var(--accent-soft);transition:.15s}
.card:hover .cta{background:var(--accent);border-color:var(--accent);color:#fff}
.card.is-sold .ph img{filter:grayscale(1) opacity(.62)}
.card.is-sold .name{color:#7b8290;font-weight:600}
.card.is-sold .price,.card.is-sold .cta{display:none}
.soldnote{margin-top:auto;padding-top:9px;font-size:12.5px;color:var(--dim2);font-weight:600}

/* ---------- vazio ---------- */
.empty{grid-column:1/-1;text-align:center;padding:64px 20px;color:var(--dim);background:var(--card);border:1px dashed var(--line);border-radius:var(--r)}
.empty b{display:block;font-size:16px;color:var(--txt);margin-bottom:6px}

/* ---------- rodapé ---------- */
footer.site{border-top:1px solid var(--line);background:var(--card);padding:22px 0;color:var(--dim);font-size:13px;margin-top:auto}
footer.site .inner{max-width:1280px;margin:0 auto;padding:0 20px;display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}

/* ---------- responsivo ---------- */
@media(max-width:940px){
  .shell{grid-template-columns:1fr;gap:0;padding-top:16px}
  aside{position:static;display:flex;gap:12px;overflow-x:auto;padding-bottom:14px;scrollbar-width:none}
  aside::-webkit-scrollbar{display:none}
  .fgroup{min-width:210px;margin-bottom:0;flex-shrink:0}
}
@media(max-width:680px){
  .wrap,.topbar .inner,.catbar .inner{padding-left:14px;padding-right:14px}
  .topbar .inner{gap:10px}
  .brand{font-size:17px}
  .searchbox{max-width:none}
  .locchip{display:none}
  .grid{grid-template-columns:repeat(2,1fr);gap:12px}
  .body{padding:10px}
  .name{font-size:13.5px}
  .price .now{font-size:17px}
  .card .cta{font-size:12.5px;padding:8px}
  .results-head h1{font-size:17px}
}
"""

# ------------------------------------------------------------------ JS do grid

JS = r"""
const ITEMS = __ITEMS__;
const state = { q: '', cat: 'todas', conds: new Set(), sort: 'recentes', showSold: false };

function brl(v){ return 'R$ ' + v.toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2}); }
function esc(s){ return String(s==null?'':s).replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

function isSold(i){ return i.status === 'vendido'; }

function filtered(){
  let out = ITEMS.filter(i => {
    if (!state.showSold && isSold(i)) return false;
    if (state.cat !== 'todas' && (i.category || '') !== state.cat) return false;
    if (state.conds.size && !state.conds.has(i.condition_group)) return false;
    if (state.q){
      const hay = (i.name + ' ' + (i.category || '') + ' ' + (i.condition || '')).toLowerCase();
      if (!hay.includes(state.q)) return false;
    }
    return true;
  });
  if (state.sort === 'menor') out = out.slice().sort((a,b) => (a._p ?? 1e9) - (b._p ?? 1e9));
  else if (state.sort === 'maior') out = out.slice().sort((a,b) => (b._p ?? -1) - (a._p ?? -1));
  else out = out.slice().sort((a,b) => (a._i ?? 0) - (b._i ?? 0));
  return out;
}

function cardHTML(i){
  const sold = isSold(i);
  const photo = (i.photos && i.photos.length)
    ? '<img src="' + esc(i.photos[0]) + '" alt="' + esc(i.name) + '" loading="lazy">'
    : '<span class="nofoto">Sem foto</span>';
  return '<a class="card' + (sold ? ' is-sold' : '') + '" href="item/' + esc(i.id) + '.html">'
    + '<div class="ph">' + photo
    + '<span class="badge' + (sold ? ' b-sold' : '') + '">' + esc(sold ? 'Vendido' : i.status_label) + '</span></div>'
    + '<div class="body">'
    + '<div class="cat">' + esc(i.category || '') + '</div>'
    + '<div class="name">' + esc(i.name) + '</div>'
    + (i.condition ? '<div class="cond">' + esc(i.condition) + '</div>' : '')
    + (i.price_html
        ? '<div class="price"><span class="now">' + esc(i.price_html) + '</span></div>'
        : '<div class="soldnote">Item vendido</div>')
    + (sold ? '' : '<span class="cta">Ver detalhes</span>')
    + '</div></a>';
}

function render(){
  const out = filtered();
  const g = document.getElementById('grid');
  const disp = out.filter(i => !isSold(i)).length;
  if (out.length){
    g.innerHTML = out.map(cardHTML).join('');
  } else if (state.showSold && ITEMS.some(isSold)) {
    g.innerHTML = '<div class="empty"><b>Nada aqui com esses filtros</b>Remova os filtros ou limpe a busca.</div>';
  } else {
    // catalogo inteiro vendido: nao e erro, e o fim do desapego
    g.innerHTML = '<div class="empty"><b>Tudo vendido</b>Obrigado a quem levou. '
      + 'Nenhum item disponível no momento.</div>';
  }
  const vend = out.length - disp;
  let txt = disp + (disp === 1 ? ' disponível' : ' disponíveis');
  if (vend) txt += ' · ' + vend + (vend === 1 ? ' vendido' : ' vendidos');
  document.getElementById('count').textContent = txt;
}

document.getElementById('q').addEventListener('input', e => { state.q = e.target.value.trim().toLowerCase(); render(); });
document.getElementById('sort').addEventListener('change', e => { state.sort = e.target.value; render(); });
document.getElementById('showsold').addEventListener('change', e => { state.showSold = e.target.checked; render(); });
document.querySelectorAll('.catbar button').forEach(b => b.addEventListener('click', () => {
  state.cat = b.dataset.cat;
  document.querySelectorAll('.catbar button').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
  render();
}));
document.querySelectorAll('input[name=cond]').forEach(c => c.addEventListener('change', () => {
  c.checked ? state.conds.add(c.value) : state.conds.delete(c.value);
  render();
}));
document.getElementById('clear').addEventListener('click', () => {
  state.q = ''; state.cat = 'todas'; state.conds.clear(); state.sort = 'recentes'; state.showSold = false;
  document.getElementById('q').value = '';
  document.getElementById('sort').value = 'recentes';
  document.getElementById('showsold').checked = false;
  document.querySelectorAll('input[name=cond]').forEach(c => { c.checked = false; });
  document.querySelectorAll('.catbar button').forEach(x => x.setAttribute('aria-pressed', String(x.dataset.cat === 'todas')));
  render();
});

// aceita ?q= vindo da busca da pagina de item
(function(){
  var m = new URLSearchParams(location.search).get('q');
  if (m){ state.q = m.toLowerCase(); document.getElementById('q').value = m; render(); }
})();
render();
"""


# ------------------------------------------------------------------ index

def render_index(items: list[dict], meta: dict) -> str:
    """items ja vem preparados por build.py (com status_label, price_html, _p)."""
    live = [i for i in items if i["status"] != "vendido"]
    cats = [c for c in CATEGORY_ORDER if any(i.get("category") == c for i in items)]
    extras = sorted({str(i.get("category")) for i in items
                     if i.get("category") and i["category"] not in cats})
    cats += extras

    # condicoes presentes nos dados: nao oferecer filtro que nao filtra nada
    groups = {i.get("condition_group") for i in items}
    cond_boxes = ""
    if "usado" in groups:
        cond_boxes += '<label><input type="checkbox" name="cond" value="usado"> Usado</label>'
    if "novo" in groups:
        cond_boxes += '<label><input type="checkbox" name="cond" value="novo"> Novo</label>'
    cond_block = f'<div class="fgroup"><h3>Condição</h3>{cond_boxes}</div>' if cond_boxes else ""

    cat_buttons = "".join(
        f'<button data-cat="{esc(c)}" aria-pressed="false">{esc(c)}</button>' for c in cats
    )

    subtitle = meta.get("subtitle") or "Itens usados em bom estado"

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='88'%3E%F0%9F%93%A6%3C/text%3E%3C/svg%3E">
<title>{esc(BRAND)} — {esc(subtitle)}</title>
<meta name="description" content="{esc(subtitle)}">
<meta property="og:title" content="{esc(BRAND)}">
<meta property="og:description" content="{esc(subtitle)}">
<meta name="twitter:card" content="summary">
<style>{CSS}</style>
</head>
<body>

<div class="topbar">
  <div class="inner">
    <a class="brand" href="index.html">{esc(BRAND)}<span>.</span></a>
    <div class="searchbox">
      <input id="q" type="search" placeholder="O que você procura?" aria-label="Buscar item" autocomplete="off">
      <button type="button" aria-hidden="true">Buscar</button>
    </div>
    <span class="locchip">São Paulo, SP</span>
  </div>
</div>

<div class="catbar">
  <div class="inner">
    <button data-cat="todas" aria-pressed="true">Todos</button>
    {cat_buttons}
  </div>
</div>

<div class="wrap">
  <div class="shell">

    <aside>
      {cond_block}
      <div class="fgroup">
        <h3>Mostrar</h3>
        <label><input type="checkbox" id="showsold"> Itens vendidos</label>
      </div>
      <div class="fgroup">
        <h3>Ordenar</h3>
        <select id="sort">
          <option value="recentes">Mais recentes</option>
          <option value="menor">Menor preço</option>
          <option value="maior">Maior preço</option>
        </select>
      </div>
      <button class="fclear" id="clear">Limpar filtros</button>
    </aside>

    <main>
      <div class="results-head">
        <h1>Anúncios</h1>
        <span class="n"><b id="count"></b></span>
      </div>
      <div class="grid" id="grid"></div>
    </main>

  </div>
</div>

<footer class="site">
  <div class="inner">
    <span>{esc(BRAND)} — venda de itens pessoais</span>
    <span>Retirada combinada com o vendedor</span>
  </div>
</footer>

<script>
{JS.replace('__ITEMS__', json.dumps(items, ensure_ascii=False))}
</script>
</body>
</html>
"""


# ------------------------------------------------------------------ detalhe

ITEM_CSS = """
.detail{max-width:1200px;margin:0 auto;padding:20px 20px 70px;width:100%;flex:1}
.crumb{font-size:13px;color:var(--dim);margin-bottom:16px}
.crumb a{text-decoration:none;color:var(--dim)}
.crumb a:hover{color:var(--accent)}
.dcols{display:grid;grid-template-columns:1.35fr 1fr;gap:34px;align-items:start}
.gal{display:grid;gap:10px}
.gal .main{position:relative;aspect-ratio:4/3;background:linear-gradient(135deg,#f1f2f4,#e7e9ec);border:1px solid var(--line);border-radius:var(--r);overflow:hidden;display:flex;align-items:center;justify-content:center}
.gal .main img{width:100%;height:100%;object-fit:cover;display:block}
.thumbs{display:flex;gap:9px;flex-wrap:wrap}
.thumbs img{width:76px;height:76px;object-fit:cover;border-radius:8px;border:1px solid var(--line);cursor:pointer;transition:.15s}
.thumbs img:hover{border-color:var(--accent)}
.thumbs img[aria-current="true"]{border-color:var(--accent);box-shadow:0 0 0 2px var(--accent-soft)}
.buy{position:sticky;top:132px;background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:20px;box-shadow:var(--shadow)}
.buy .cat{font-size:11.5px;font-weight:750;letter-spacing:.07em;text-transform:uppercase;color:var(--dim2);margin-bottom:9px}
.buy h1{font-size:25px;font-weight:700;line-height:1.24;letter-spacing:-.02em}
.buy .cond{color:var(--dim);font-size:14px;margin-top:7px}
.buy .pricebig{margin:20px 0 4px;display:flex;align-items:baseline;gap:9px;flex-wrap:wrap}
.buy .pricebig .now{font-size:36px;font-weight:750;letter-spacing:-.03em;color:var(--accent)}
.buy .pricebig .undef{font-size:24px;font-weight:700;color:var(--dim)}
.buy .pricebig .lbl{font-size:13px;color:var(--dim2)}
.btn-wa{display:flex;align-items:center;justify-content:center;gap:9px;width:100%;margin-top:18px;background:var(--accent);color:#fff;font-size:16px;font-weight:700;text-decoration:none;padding:15px;border-radius:9px;border:none;cursor:pointer;transition:.15s}
.btn-wa:hover{background:#c94b08}
.btn-off{display:block;text-align:center;width:100%;margin-top:18px;background:var(--sold-bg);color:var(--sold-txt);font-size:15px;font-weight:700;padding:15px;border-radius:9px;border:1px solid var(--line)}
.seller{margin-top:16px;padding-top:16px;border-top:1px solid var(--line2);display:flex;gap:11px;align-items:center}
.av{width:42px;height:42px;border-radius:50%;background:var(--accent-soft);border:1px solid var(--accent-line);display:flex;align-items:center;justify-content:center;font-weight:750;color:var(--accent);font-size:16px;flex-shrink:0}
.seller .who{font-size:14.5px;font-weight:650}
.seller .where{font-size:12.5px;color:var(--dim)}
.pickup{margin-top:12px;font-size:13px;color:var(--dim);display:flex;align-items:center;gap:7px}
.report{margin-top:14px;font-size:12px;color:var(--dim2);text-decoration:none;display:inline-block}
.report:hover{color:var(--dim)}
.secs{margin-top:38px;display:grid;gap:22px}
.sec{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:20px;box-shadow:var(--shadow)}
.sec h2{font-size:13px;font-weight:750;letter-spacing:.07em;text-transform:uppercase;color:var(--dim);margin-bottom:14px}
.sec p{font-size:15px;line-height:1.7;color:#374151}
.kv{display:grid;grid-template-columns:1fr 1fr;gap:0 30px}
.kv .row{display:flex;justify-content:space-between;gap:14px;padding:11px 0;border-bottom:1px solid var(--line2);font-size:14.5px}
.kv .row:nth-last-child(-n+2){border-bottom:none}
.kv .k{color:var(--dim)}
.kv .v{font-weight:600;text-align:right}
footer.site{border-top:1px solid var(--line);background:var(--card);padding:22px 0;color:var(--dim);font-size:13px;margin-top:auto}
footer.site .inner{max-width:1280px;margin:0 auto;padding:0 20px;display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}
@media(max-width:920px){
  .dcols{grid-template-columns:1fr;gap:22px}
  .buy{position:static}
  .kv{grid-template-columns:1fr}
  .kv .row:nth-last-child(-n+2){border-bottom:1px solid var(--line2)}
  .kv .row:last-child{border-bottom:none}
}
@media(max-width:680px){
  .detail{padding:14px 14px 50px}
  .buy h1{font-size:21px}
  .buy .pricebig .now{font-size:30px}
  .buy{padding:16px}
}
"""


def render_item(item: dict, meta: dict, total_items: int, wa: str) -> str:
    sold = item.get("status") == "vendido"
    price = public_price(item)
    cat = item.get("category") or ""
    name = item["name"]

    if sold:
        title = f"{name} — vendido"
        desc = "Este item já foi vendido."
    else:
        title = f"{name} — {price}"
        desc = f"{price} · {cat}".strip(" ·")

    photos = item.get("photos") or []
    if photos:
        main = f'<img id="mainimg" src="../{esc(photos[0])}" alt="{esc(name)}">'
        thumbs = "".join(
            f'<img src="../{esc(p)}" alt="{esc(name)}" data-full="../{esc(p)}" aria-current="{"true" if n == 0 else "false"}">'
            for n, p in enumerate(photos)
        ) if len(photos) > 1 else ""
    else:
        main = '<span class="nofoto">Sem foto</span>'
        thumbs = ""

    if sold:
        cta = '<div class="btn-off">Item vendido</div>'
    elif wa:
        link = ("https://wa.me/" + re.sub(r"\D", "", wa)
                + "?text=" + quote(meta.get("whatsapp_message", "").replace("{item}", name)))
        cta = (f'<a class="btn-wa" href="{esc(link)}" target="_blank" rel="noopener">'
               f'<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
               f'<path d="M17.47 14.38c-.3-.15-1.76-.87-2.03-.97-.27-.1-.47-.15-.67.15-.2.3-.77.97-.94 1.17-.17.2-.35.22-.65.07-.3-.15-1.26-.46-2.4-1.48-.89-.79-1.49-1.76-1.66-2.06-.17-.3-.02-.46.13-.61.13-.13.3-.35.45-.52.15-.17.2-.3.3-.5.1-.2.05-.37-.02-.52-.07-.15-.67-1.61-.92-2.2-.24-.58-.49-.5-.67-.51h-.57c-.2 0-.52.07-.79.37-.27.3-1.04 1.02-1.04 2.48 0 1.46 1.06 2.87 1.21 3.07.15.2 2.09 3.2 5.07 4.48.71.31 1.26.49 1.69.63.71.23 1.36.19 1.87.12.57-.09 1.76-.72 2.01-1.41.25-.7.25-1.29.17-1.41-.07-.13-.27-.2-.57-.35zM12.02 21.5h-.01a9.4 9.4 0 0 1-4.79-1.31l-.34-.2-3.56.93.95-3.47-.22-.36a9.38 9.38 0 0 1-1.44-5.01c0-5.19 4.23-9.41 9.42-9.41 2.51 0 4.88.98 6.66 2.76a9.35 9.35 0 0 1 2.76 6.66c0 5.19-4.23 9.41-9.43 9.41zM20.5 3.49A11.8 11.8 0 0 0 12.02 0C5.5 0 .2 5.3.2 11.81c0 2.08.54 4.11 1.58 5.9L0 24l6.44-1.69a11.77 11.77 0 0 0 5.58 1.42h.01c6.51 0 11.81-5.3 11.81-11.81 0-3.16-1.23-6.12-3.34-8.43z"/></svg>'
               f'Falar com o vendedor</a>')
    else:
        cta = '<div class="btn-off">Contato em breve</div>'

    specs_html = ""
    if item.get("specs"):
        rows = "".join(
            f'<div class="row"><span class="k">{esc(k)}</span><span class="v">{esc(v)}</span></div>'
            for k, v in item["specs"].items()
        )
        specs_html = f'<div class="sec"><h2>Características</h2><div class="kv">{rows}</div></div>'

    # Descricao publica: so o que interessa ao comprador. Notas internas
    # (plataforma, taxa, disputa) nunca vao para o publico.
    about = ""
    if item.get("public_notes"):
        about = f'<div class="sec"><h2>Descrição</h2><p>{esc(item["public_notes"])}</p></div>'

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="{'noindex' if sold else 'index,follow'}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='88'%3E%F0%9F%93%A6%3C/text%3E%3C/svg%3E">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta property="og:type" content="product">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc((meta.get('base_url') or '').rstrip('/'))}/item/{esc(item['id'])}.html">
{f'<meta property="og:image" content="{esc((meta.get("base_url") or "").rstrip("/"))}/{esc(photos[0])}">' if photos else ''}
<meta name="twitter:card" content="summary_large_image">
<style>{CSS}{ITEM_CSS}</style>
</head>
<body>

<div class="topbar">
  <div class="inner">
    <a class="brand" href="../index.html">{esc(BRAND)}<span>.</span></a>
    <div class="searchbox">
      <input type="search" id="q2" placeholder="O que você procura?" aria-label="Buscar item">
      <button type="button" onclick="location.href='../index.html'">Buscar</button>
    </div>
    <span class="locchip">São Paulo, SP</span>
  </div>
</div>

<div class="detail">

  <div class="crumb">
    <a href="../index.html">Início</a> / <a href="../index.html">{esc(cat)}</a> / {esc(name)}
  </div>

  <div class="dcols">

    <div class="gal">
      <div class="main">{main}</div>
      {f'<div class="thumbs">{thumbs}</div>' if thumbs else ''}
    </div>

    <div class="buy">
      <div class="cat">{esc(cat)}</div>
      <h1>{esc(name)}</h1>
      {f'<div class="cond">{esc(item["condition"])}</div>' if item.get("condition") else ''}
      <div class="pricebig">
        {f'<span class="now">{esc(price)}</span>' if price else '<span class="undef">Vendido</span>'}
        {'' if sold else f'<span class="lbl">{esc("em negociação" if item.get("status") == "negociando" else "à vista")}</span>'}
      </div>
      {cta}
      <div class="seller">
        <div class="av">I</div>
        <div>
          <div class="who">{esc(meta.get("seller_name") or "Vendedor")}</div>
          <div class="where">São Paulo, SP</div>
        </div>
      </div>
      <div class="pickup">Retirada combinada com o vendedor</div>
      <a class="report" href="#report">Denunciar anúncio</a>
    </div>

  </div>

  <div class="secs">
    {about}
    {specs_html}
  </div>

</div>

<footer class="site">
  <div class="inner">
    <span>{esc(BRAND)} — venda de itens pessoais</span>
    <span><a href="../index.html">ver todos os anúncios</a></span>
  </div>
</footer>

<script>
(function(){{
  var main = document.getElementById('mainimg');
  if (!main) return;
  document.querySelectorAll('.thumbs img').forEach(function(t){{
    t.addEventListener('click', function(){{
      main.src = t.dataset.full;
      document.querySelectorAll('.thumbs img').forEach(function(x){{ x.setAttribute('aria-current','false'); }});
      t.setAttribute('aria-current','true');
    }});
  }});
}})();
function nearest(){{
  var q = document.getElementById('q2').value.trim();
  location.href = '../index.html' + (q ? '?q=' + encodeURIComponent(q) : '');
}}
document.getElementById('q2').addEventListener('keydown', function(e){{ if (e.key === 'Enter') nearest(); }});
</script>
</body>
</html>
"""
