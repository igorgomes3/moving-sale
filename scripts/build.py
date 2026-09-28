#!/usr/bin/env python3
"""
Gerador do catalogo estatico do Moving Sale.

Le data/inventory.json (fonte de verdade) + data/fees.json e produz site/:
  - site/index.html           catalogo publico (auto-contido, sem deps)
  - site/data/inventory.json  copia para a pagina /admin.html ler same-origin
  - site/data/fees.json       idem
  - site/copys.md             copy de anuncio por item ainda a venda
  - site/resumo.md            relatorio financeiro (bruto, taxas, liquido)

Uso:
  python3 scripts/build.py            # gera
  python3 scripts/build.py --check    # gera e valida (nao escreve nada se falhar)
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE = ROOT / "site"

STATUS_LABEL = {
    "a_venda": "a venda",
    "negociando": "negociando",
    "reservado": "reservado",
    "vendido": "vendido",
}

PAYMENT_LABEL = {
    "recebido": "recebido",
    "pendente": "a liberar",
    "disputa": "em disputa",
}


# ---------------------------------------------------------------- taxas

def fixed_fee(bands: list[dict], price: float) -> float:
    for band in bands:
        if band["max_price"] is None or price <= band["max_price"]:
            return float(band["fixed"])
    return 0.0


def envio_protegido(amount: float) -> float:
    if amount <= 25.63:
        return 0.0
    return round((amount - 25.63) * 0.015 + 1.49, 2)


def item_fee(item: dict, fees: dict) -> float:
    """Taxa total da plataforma para um item vendido."""
    gross = item.get("sold_price")
    if gross is None:
        return 0.0
    if item.get("platform") != "enjoei":
        return 0.0
    # Liquido confirmado no extrato tem precedencia sobre o calculo.
    net = item.get("net_received")
    if net is not None:
        return round(gross - net, 2)
    mode = item.get("enjoei_mode") or "classico"
    spec = fees["enjoei"]["modes"][mode]
    total = gross * spec["commission_pct"] / 100.0
    total += fixed_fee(spec["fixed_fee_bands"], gross)
    if item.get("envio_protegido"):
        total += envio_protegido(gross - total)
    return round(total, 2)


def totals(inv: dict, fees: dict) -> dict:
    sold = [i for i in inv["items"] if i.get("status") == "vendido"]
    gross = sum(i.get("sold_price") or 0 for i in sold)
    fee_sum = sum(item_fee(i, fees) for i in sold)
    delivery = sum(i.get("delivery_cost") or 0 for i in sold)
    net = gross - fee_sum - delivery

    by_status = {}
    for key in ("recebido", "pendente", "disputa"):
        by_status[key] = sum(
            (i.get("sold_price") or 0) - item_fee(i, fees)
            for i in sold
            if i.get("payment_status") == key
        )

    potential = sum(
        i.get("asking_price") or 0
        for i in inv["items"]
        if i.get("status") in ("a_venda", "negociando", "reservado")
    )

    return {
        "sold_count": len(sold),
        "gross": gross,
        "fees": fee_sum,
        "delivery": delivery,
        "net": net,
        "received": by_status["recebido"],
        "pending": by_status["pendente"],
        "dispute": by_status["disputa"],
        "potential": potential,
        "projection": net + potential,
    }


# ---------------------------------------------------------------- helpers

def brl(value) -> str:
    if value is None:
        return "—"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def esc(text) -> str:
    return html.escape(str(text if text is not None else ""), quote=True)


def sort_items(items: list[dict]) -> list[dict]:
    """A venda primeiro (mais caros primeiro, sem preco por ultimo), vendidos ao final."""
    order = {"a_venda": 0, "negociando": 1, "reservado": 2, "vendido": 3}

    def price_key(i: dict) -> float:
        p = i.get("asking_price") if i.get("status") != "vendido" else i.get("sold_price")
        if p is None:
            p = i.get("asking_price") or i.get("sold_price")
        # sem preco vai para o fim do seu grupo
        return -(p if p is not None else -1)

    return sorted(items, key=lambda i: (order.get(i.get("status", "a_venda"), 9), price_key(i)))


# ---------------------------------------------------------------- HTML

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0f1115;--card:#181c23;--card2:#1f242d;--line:#2a303b;
  --txt:#e8eaed;--dim:#9aa3b2;--accent:#4ade80;--accent2:#22c55e;
  --sold:#4b5563;--warn:#fbbf24;--danger:#f87171;--radius:14px;
}
body{background:var(--bg);color:var(--txt);font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:32px 20px 80px}
header{margin-bottom:28px}
h1{font-size:clamp(26px,4vw,40px);letter-spacing:-.02em;line-height:1.15}
.sub{color:var(--dim);margin-top:8px;font-size:17px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:26px 0 30px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:14px 16px}
.stat .k{color:var(--dim);font-size:12px;text-transform:uppercase;letter-spacing:.07em;font-weight:600}
.stat .v{font-size:23px;font-weight:700;margin-top:5px;letter-spacing:-.01em}
.stat .n{color:var(--dim);font-size:12px;margin-top:2px}
.stat.hi .v{color:var(--accent)}
.stat.warn .v{color:var(--warn)}
.stat.risk .v{color:var(--danger)}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:22px}
.filters button{
  background:var(--card);color:var(--dim);border:1px solid var(--line);border-radius:999px;
  padding:9px 17px;font-size:14px;font-weight:600;cursor:pointer;font-family:inherit;transition:.15s
}
.filters button:hover{color:var(--txt);border-color:#3a4250}
.filters button[aria-pressed="true"]{background:var(--accent);color:#06240f;border-color:var(--accent)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(258px,1fr));gap:18px;align-items:stretch}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;display:flex;flex-direction:column;transition:.18s}
.card:hover{border-color:#3a4250;transform:translateY(-2px)}
.cardlink{display:block;text-decoration:none;color:inherit}
.namelink{text-decoration:none;color:inherit}
.namelink:hover .name{color:var(--accent)}
.ph{aspect-ratio:16/10;max-height:210px;background:linear-gradient(135deg,#1f242d,#252b36);display:flex;align-items:center;justify-content:center;color:#8a93a6;font-size:13px;position:relative;overflow:hidden}
.ph img{width:100%;height:100%;object-fit:cover;display:block}
.nofoto{color:#8a93a6;font-size:12.5px;font-weight:600;letter-spacing:.04em;text-transform:uppercase}
.badges{position:absolute;top:10px;left:10px;display:flex;gap:6px;flex-wrap:wrap}
.badge{font-size:11px;font-weight:700;padding:4px 9px;border-radius:999px;text-transform:uppercase;letter-spacing:.05em;backdrop-filter:blur(8px)}
.b-a_venda{background:rgba(74,222,128,.9);color:#06240f}
.b-negociando{background:rgba(251,191,36,.9);color:#3d2c00}
.b-reservado{background:rgba(96,165,250,.9);color:#04203d}
.b-vendido{background:rgba(75,85,99,.92);color:#e5e7eb}
.body{padding:15px 16px 16px;display:flex;flex-direction:column;gap:9px;flex:1}
.cat{color:var(--dim);font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.06em}
.name{font-size:16.5px;font-weight:650;line-height:1.32}
.cond{color:var(--dim);font-size:13.5px}
.specs{color:var(--dim);font-size:13px;line-height:1.45;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.notes{color:var(--dim);font-size:13px;line-height:1.45;border-top:1px dashed var(--line);padding-top:9px;margin-top:2px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.price{margin-top:auto;padding-top:12px;display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.price .now{font-size:21px;font-weight:750;letter-spacing:-.01em}
.price .undef{font-size:16px;font-weight:650;color:var(--txt);opacity:.85}
.price .was{color:var(--dim);font-size:14px;text-decoration:line-through}
.price .lbl{color:var(--dim);font-size:12.5px}
.card.sold .ph{filter:grayscale(1) brightness(.62)}
.card.sold .name,.card.sold .price .now{color:var(--dim)}
.cta{display:block;text-align:center;background:var(--accent);color:#06240f;font-weight:700;font-size:14.5px;padding:11px;border-radius:10px;text-decoration:none;border:none;cursor:pointer;margin-top:4px}
.cta:hover{background:var(--accent2)}
.cta.ghost{background:transparent;border:1px solid var(--line);color:var(--dim);cursor:default}
.cta.ghost:hover{background:transparent}
.cta.link{background:transparent;border:1px solid var(--line);color:var(--txt);margin-top:8px}
.cta.link:hover{background:var(--card2);border-color:#3a4250}
.empty{text-align:center;color:var(--dim);padding:70px 20px}
footer{margin-top:56px;padding-top:24px;border-top:1px solid var(--line);color:var(--dim);font-size:13.5px;display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}
footer a{color:var(--dim)}
@media(max-width:520px){.wrap{padding:22px 14px 60px}.grid{grid-template-columns:1fr 1fr;gap:12px}.name{font-size:14.5px}.price .now{font-size:18px}.body{padding:12px;gap:7px}.stats{grid-template-columns:1fr 1fr}}
"""

JS = """
const ITEMS = __ITEMS__;
const META  = __META__;
const WA    = META.whatsapp;
let filter = 'todos';

function brl(v){ return v==null ? '—' : 'R$ ' + v.toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2}); }
function esc(s){ return String(s==null?'':s).replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

function render(){
  const grid = document.getElementById('grid');
  const list = ITEMS.filter(i => {
    if (filter === 'todos') return true;
    if (filter === 'a_venda') return i.status === 'a_venda' || i.status === 'negociando' || i.status === 'reservado';
    return i.status === filter;
  });
  if (!list.length){ grid.innerHTML = '<div class="empty">Nada aqui.</div>'; return; }
  grid.innerHTML = list.map(card).join('');
}

function card(i){
  const sold = i.status === 'vendido';
  const price = sold ? i.sold_price : i.asking_price;
  let priceHtml;
  if (price != null){
    const lbl = sold ? 'vendido' : (i.status === 'negociando' ? 'em negociação' : 'à vista');
    priceHtml = '<div class="price"><span class="now">' + brl(price) + '</span><span class="lbl">' + lbl + '</span></div>';
  } else {
    priceHtml = '<div class="price"><span class="undef">Preço a definir</span></div>';
  }

  const photo = (i.photos && i.photos.length)
    ? '<img src="' + esc(i.photos[0]) + '" alt="' + esc(i.name) + '" loading="lazy">'
    : '<span class="nofoto">sem foto</span>';

  let cta;
  if (sold){
    cta = '<span class="cta ghost">' + (i.payment_status === 'disputa' ? 'em disputa' : 'já foi') + '</span>';
  } else if (WA){
    const link = 'https://wa.me/' + esc(String(WA).replace(/\\D/g,'')) + '?text=' + encodeURIComponent((META.whatsapp_message||'').replace('{item}', i.name));
    cta = '<a class="cta" href="' + link + '" target="_blank" rel="noopener">Tenho interesse</a>';
  } else if (META.contact_email){
    const link = 'mailto:' + esc(META.contact_email) + '?subject=' + encodeURIComponent('Interesse: ' + i.name);
    cta = '<a class="cta" href="' + link + '">Tenho interesse</a>';
  } else {
    cta = '<a class="cta" href="#item-' + esc(i.id) + '" data-copy="' + esc(i.name) + '">Copiar nome do item</a>';
  }

  const specs = i.specs ? '<div class="specs">' + Object.values(i.specs).map(esc).join(' · ') + '</div>' : '';
  const note = (!sold && i.notes) ? '<div class="notes">' + esc(i.notes) + '</div>' : '';

  return '<article class="card ' + (sold?'sold':'') + '" id="item-' + esc(i.id) + '" data-status="' + i.status + '">'
    + '<a class="cardlink" href="item/' + esc(i.id) + '.html" aria-label="Ver ' + esc(i.name) + '">'
    + '<div class="ph">' + photo + '<div class="badges"><span class="badge b-' + i.status + '">' + esc(i.status_label) + '</span></div></div>'
    + '</a>'
    + '<div class="body">'
    +   '<div class="cat">' + esc(i.category) + (i.qty && i.qty > 1 ? ' · ' + i.qty + ' itens' : '') + '</div>'
    +   '<a class="namelink" href="item/' + esc(i.id) + '.html"><div class="name">' + esc(i.name) + '</div></a>'
    +   (i.condition ? '<div class="cond">' + esc(i.condition) + '</div>' : '')
    +   specs + note
    +   priceHtml
    +   cta
    +   '<a class="cta link" href="item/' + esc(i.id) + '.html">Ver detalhes e compartilhar</a>'
    + '</div></article>';
}

document.addEventListener('click', (e) => {
  const el = e.target.closest('[data-copy]');
  if (!el) return;
  e.preventDefault();
  const name = el.dataset.copy;
  (navigator.clipboard ? navigator.clipboard.writeText(name) : Promise.reject())
    .then(() => { el.textContent = 'Copiado!'; setTimeout(() => el.textContent = 'Copiar nome do item', 1500); })
    .catch(() => { prompt('Copie o nome do item:', name); });
});

document.querySelectorAll('.filters button').forEach(b => {
  b.addEventListener('click', () => {
    filter = b.dataset.f;
    document.querySelectorAll('.filters button').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
    render();
  });
});
render();
"""


def build_index(inv: dict, fees: dict, t: dict) -> str:
    items = []
    for i in sort_items(inv["items"]):
        merged = dict(i)
        merged["status_label"] = STATUS_LABEL.get(i.get("status"), i.get("status"))
        items.append(merged)

    meta = dict(inv["meta"])
    wa = meta.get("whatsapp") or ""

    stats = f"""
    <div class="stats">
      <div class="stat hi"><div class="k">Já recebido</div><div class="v">{brl(t['received'])}</div><div class="n">Pix / Marketplace</div></div>
      <div class="stat"><div class="k">A liberar</div><div class="v">{brl(t['pending'])}</div><div class="n">aguardando plataforma</div></div>
      <div class="stat risk"><div class="k">Em disputa</div><div class="v">{brl(t['dispute'])}</div><div class="n">risco de reversão</div></div>
      <div class="stat"><div class="k">Ainda à venda</div><div class="v">{brl(t['potential'])}</div><div class="n">potencial</div></div>
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E%F0%9F%8F%B7%EF%B8%8F%3C/text%3E%3C/svg%3E">
<title>{esc(meta.get('title','Desapego'))}</title>
<meta name="description" content="{esc(meta.get('subtitle',''))}">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>{esc(meta.get('title','Desapego'))}</h1>
    <p class="sub">{esc(meta.get('subtitle',''))}</p>
  </header>
  {stats}
  <div class="filters">
    <button data-f="todos" aria-pressed="true">Todos</button>
    <button data-f="a_venda" aria-pressed="false">À venda</button>
    <button data-f="vendido" aria-pressed="false">Vendidos</button>
  </div>
  <div class="grid" id="grid"></div>
  <footer>
    <span>{len(items)} itens · {t['sold_count']} vendidos</span>
    <span>Atualizado em {datetime.now(timezone.utc).strftime('%d/%m/%Y')} · retirada em São Paulo</span>
  </footer>
</div>
<script>
{JS.replace('__ITEMS__', json.dumps(items, ensure_ascii=False, indent=None)).replace('__META__', json.dumps(meta, ensure_ascii=False))}
</script>
</body>
</html>
"""


def build_item_pages(inv: dict, fees: dict, t: dict) -> int:
    """Gera site/item/<id>.html — uma pagina por item, com OG tags para
    preview no WhatsApp. O link e o que o Igor compartilha."""
    meta = inv["meta"]
    base = (meta.get("base_url") or "").rstrip("/")
    wa = meta.get("whatsapp") or ""
    out_dir = SITE / "item"
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for item in inv["items"]:
        sold = item.get("status") == "vendido"
        price = item.get("sold_price") if sold else item.get("asking_price")
        price_txt = brl(price) if price is not None else "Preço a definir"

        title = item["name"]
        if not sold and price is not None:
            title = f"{item['name']} — {price_txt}"

        # foto para o preview
        og_img = ""
        if item.get("photos"):
            rel = item["photos"][0]
            og_img = f"{base}/{rel}" if base else rel

        desc_bits = [b for b in (item.get("condition"), item.get("category")) if b]
        if sold:
            desc = "Vendido. " + " · ".join(desc_bits)
        else:
            desc = f"{price_txt} · " + " · ".join(desc_bits)
        desc += ". Retirada em São Paulo."

        status_label = STATUS_LABEL.get(item.get("status"), item.get("status"))

        # galeria
        photos = item.get("photos") or []
        if photos:
            gallery = "".join(
                f'<img src="../{esc(p)}" alt="{esc(item["name"])}" loading="lazy">'
                for p in photos
            )
        else:
            gallery = '<div class="ph big"><span class="nofoto">sem foto</span></div>'

        # specs
        specs_html = ""
        if item.get("specs"):
            rows = "".join(
                f'<div class="kv"><span class="k">{esc(k)}</span><span class="v">{esc(v)}</span></div>'
                for k, v in item["specs"].items()
            )
            specs_html = f'<div class="panel"><h2>Especificações</h2>{rows}</div>'

        # CTA
        if sold:
            cta = f'<div class="cta ghost big">{esc("já foi" if item.get("payment_status") != "disputa" else "em disputa")}</div>'
        elif wa:
            link = ("https://wa.me/" + re.sub(r"\D", "", wa)
                    + "?text=" + quote(meta.get("whatsapp_message", "").replace("{item}", item["name"])))
            cta = f'<a class="cta big" href="{esc(link)}" target="_blank" rel="noopener">Tenho interesse</a>'
        else:
            cta = '<div class="cta ghost big">chamar no WhatsApp</div>'

        notes_html = ""
        if item.get("notes"):
            notes_html = f'<div class="panel"><h2>Sobre o item</h2><p class="body">{esc(item["notes"])}</p></div>'

        back = "index.html" if not base else "index.html"

        page = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="{'noindex' if sold else 'index,follow'}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E%F0%9F%8F%B7%EF%B8%8F%3C/text%3E%3C/svg%3E">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(base)}/item/{esc(item['id'])}.html">
{'<meta property="og:image" content="' + esc(og_img) + '">' if og_img else ''}
<meta name="twitter:card" content="summary_large_image">
<style>{CSS}{ITEM_CSS}</style>
</head>
<body>
<div class="wrap narrow">
  <a class="back" href="../{back}">← voltar ao catálogo</a>

  <div class="gal">
    {gallery}
  </div>

  <div class="hd-row">
    <span class="badge b-{esc(item.get('status',''))}">{esc(status_label)}</span>
    <span class="cat">{esc(item.get('category') or '')}</span>
  </div>

  <h1 class="item-h1">{esc(item['name'])}</h1>
  {f'<p class="cond">{esc(item["condition"])}</p>' if item.get("condition") else ''}

  <div class="price-big">
    <span class="now">{esc(price_txt)}</span>
    {f'<span class="lbl">{esc("vendido por") if sold else ("em negociação" if item.get("status") == "negociando" else "à vista")}</span>'}
  </div>

  {cta}

  {specs_html}
  {notes_html}

  <div class="share">
    <button class="cta ghost" id="btnShare" data-url="{esc(base)}/item/{esc(item['id'])}.html">Copiar link deste item</button>
  </div>

  <footer>
    <span>{esc(inv['meta'].get('title','') or '')}</span>
    <span><a href="../index.html">ver todos os {len(inv['items'])} itens</a></span>
  </footer>
</div>
<script>
document.getElementById('btnShare').addEventListener('click', function(){{
  var url = this.dataset.url;
  var b = this;
  var done = function(){{ b.textContent = 'Link copiado!'; setTimeout(function(){{ b.textContent='Copiar link deste item'; }}, 1500); }};
  if (navigator.share) {{ navigator.share({{title: document.title, url: url}}).then(done).catch(function(){{}}); }}
  else if (navigator.clipboard) {{ navigator.clipboard.writeText(url).then(done).catch(function(){{ prompt('Copie o link:', url); }}); }}
  else {{ prompt('Copie o link:', url); }}
}});
</script>
</body>
</html>
"""
        (out_dir / f"{item['id']}.html").write_text(page, encoding="utf-8")
        count += 1

    return count


ITEM_CSS = """
.wrap.narrow{max-width:820px}
.back{display:inline-block;color:var(--dim);text-decoration:none;font-size:14px;margin-bottom:18px}
.back:hover{color:var(--txt)}
.gal{display:grid;gap:10px;margin-bottom:20px}
.gal img{width:100%;border-radius:var(--radius);display:block;background:var(--card2)}
.gal img:first-child{max-height:520px;object-fit:cover}
.gal:has(img:nth-child(2)){grid-template-columns:1fr 1fr}
.gal:has(img:nth-child(2)) img:first-child{grid-column:1/-1;max-height:420px}
.ph.big{aspect-ratio:16/10;max-height:420px;background:linear-gradient(135deg,#1f242d,#252b36);display:flex;align-items:center;justify-content:center;border-radius:var(--radius)}
.hd-row{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.item-h1{font-size:clamp(22px,3.4vw,32px);letter-spacing:-.02em;line-height:1.2}
.cond{color:var(--dim);margin-top:6px;font-size:15px}
.price-big{margin:18px 0 16px;display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.price-big .now{font-size:34px;font-weight:750;letter-spacing:-.02em}
.price-big .lbl{color:var(--dim);font-size:14px}
.cta.big{font-size:16.5px;padding:15px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:16px;margin-top:16px}
.panel h2{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--dim);margin-bottom:12px}
.panel .body{color:var(--txt);font-size:15px;line-height:1.6}
.kv{display:flex;justify-content:space-between;gap:16px;padding:7px 0;border-bottom:1px solid var(--line);font-size:14.5px}
.kv:last-child{border-bottom:none}
.kv .k{color:var(--dim);text-transform:capitalize;flex-shrink:0}
.kv .v{text-align:right}
.share{margin-top:18px}
@media(max-width:520px){.gal:has(img:nth-child(2)){grid-template-columns:1fr}.price-big .now{font-size:28px}}
"""


def build_copys(inv: dict) -> str:
    out = ["# Copys de anúncio — rascunhos para revisar e postar\n",
           "> REGRA: nada é publicado automaticamente. Copie, revise e poste você mesmo.\n"]
    for i in inv["items"]:
        if i.get("status") not in ("a_venda", "negociando", "reservado"):
            continue
        price = i.get("asking_price")
        out.append(f"\n---\n\n## {i['name']}\n")
        out.append(f"**Preço pedido:** {brl(price)}  ")
        out.append(f"**Categoria:** {i.get('category','—')}  ")
        out.append(f"**Condição:** {i.get('condition','—')}\n")
        if i.get("specs"):
            out.append("\n**Especificações**")
            for k, v in i["specs"].items():
                out.append(f"- {k}: {v}")
            out.append("")
        out.append("\n**Título (OLX/Marketplace — use as keywords de busca):**")
        out.append(f"\n```\n{i['name']}"
                   + (f" — {i.get('condition','')}" if i.get('condition') else "")
                   + f" — {brl(price)}\n```\n")
        out.append("**Descrição curta (grupo do condomínio / WhatsApp):**\n")
        out.append(f"\n```\n{i['name']} — {brl(price)}"
                   + (f"\n{i.get('condition','')}" if i.get('condition') else "")
                   + "\nRetirada no local (São Paulo). Sem entrega.\n```\n")
        out.append("**Descrição longa (OLX):**\n")
        out.append(f"\n```\n{i['name']}\n\n"
                   + (f"Condição: {i['condition']}\n" if i.get('condition') else "")
                   + (f"{i['notes']}\n" if i.get('notes') else "")
                   + f"Valor: {brl(price)}\n\nRetirada no local, em São Paulo (capital). Não faço entrega.\nPagamento por Pix ou dinheiro na retirada.\n```\n")
        if i.get("open_questions"):
            out.append("**Pendências antes de anunciar:**")
            for q in i["open_questions"]:
                out.append(f"- [ ] {q}")
            out.append("")
    return "\n".join(out)


def build_resumo(inv: dict, fees: dict, t: dict) -> str:
    lines = ["# Moving Sale — resumo financeiro\n",
             f"Gerado em {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}\n",
             "## Vendidos\n",
             "| Item | Plataforma | Bruto | Taxa | Líquido | % taxa | Situação |",
             "|---|---|---|---|---|---|---|"]
    for i in sort_items(inv["items"]):
        if i.get("status") != "vendido":
            continue
        g = i.get("sold_price") or 0
        f = item_fee(i, fees)
        n = g - f - (i.get("delivery_cost") or 0)
        pct = f"{f/g*100:.1f}%" if g else "—"
        lines.append(f"| {i['name']} | {i.get('platform') or '—'} | {brl(g)} | {brl(f)} | {brl(n)} | {pct} | {PAYMENT_LABEL.get(i.get('payment_status'), '—')} |")

    lines += ["\n## Totais\n",
              f"- Bruto: **{brl(t['gross'])}**",
              f"- Taxas de plataforma: **−{brl(t['fees'])}** ({t['fees']/t['gross']*100:.1f}% do bruto)" if t['gross'] else "- Taxas: —",
              f"- Entregas/deslocamento: **−{brl(t['delivery'])}**",
              f"- **Líquido: {brl(t['net'])}**\n",
              f"- Já recebido: {brl(t['received'])}",
              f"- A liberar: {brl(t['pending'])}",
              f"- Em disputa (risco): {brl(t['dispute'])}\n",
              f"- Potencial à venda: {brl(t['potential'])}",
              f"- **Projeção total: {brl(t['projection'])}**\n",
              "## Ainda à venda / negociando\n",
              "| Item | Pedido | Status |",
              "|---|---|---|"]
    for i in sort_items(inv["items"]):
        if i.get("status") in ("a_venda", "negociando", "reservado"):
            lines.append(f"| {i['name']} | {brl(i.get('asking_price'))} | {STATUS_LABEL.get(i['status'], i['status'])} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="valida sem publicar")
    args = ap.parse_args()

    inv = json.loads((DATA / "inventory.json").read_text(encoding="utf-8"))
    fees = json.loads((DATA / "fees.json").read_text(encoding="utf-8"))

    ids = [i["id"] for i in inv["items"]]
    dupes = {x for x in ids if ids.count(x) > 1}
    if dupes:
        print(f"ERRO: ids duplicados: {dupes}", file=sys.stderr)
        return 1
    for i in inv["items"]:
        if i.get("status") not in STATUS_LABEL:
            print(f"ERRO: status invalido em {i['id']}: {i.get('status')}", file=sys.stderr)
            return 1
        if i.get("payment_status") and i["payment_status"] not in PAYMENT_LABEL:
            print(f"ERRO: payment_status invalido em {i['id']}: {i['payment_status']}", file=sys.stderr)
            return 1

    t = totals(inv, fees)

    if SITE.exists() and not args.check:
        shutil.rmtree(SITE)
    (SITE / "data").mkdir(parents=True, exist_ok=True)

    (SITE / "index.html").write_text(build_index(inv, fees, t), encoding="utf-8")
    n_items = build_item_pages(inv, fees, t)
    (SITE / "data" / "inventory.json").write_text(json.dumps(inv, ensure_ascii=False, indent=2), encoding="utf-8")
    (SITE / "data" / "fees.json").write_text(json.dumps(fees, ensure_ascii=False, indent=2), encoding="utf-8")
    (SITE / "copys.md").write_text(build_copys(inv), encoding="utf-8")
    (SITE / "resumo.md").write_text(build_resumo(inv, fees, t), encoding="utf-8")

    admin_src = ROOT / "admin.html"
    if admin_src.exists():
        shutil.copy(admin_src, SITE / "admin.html")
    (SITE / ".nojekyll").write_text("", encoding="utf-8")

    # copia as fotos versionadas de assets/img para site/img
    assets_img = ROOT / "assets" / "img"
    if assets_img.is_dir():
        files = [p for p in assets_img.iterdir() if p.is_file()]
        if files:
            dest = SITE / "img"
            dest.mkdir(parents=True, exist_ok=True)
            for p in files:
                shutil.copy2(p, dest / p.name)
            print(f"    fotos: {len(files)} copiada(s) de assets/img/")

    # avisa se algum item aponta para foto inexistente
    for item in inv["items"]:
        for rel in item.get("photos") or []:
            if not (SITE / rel).exists():
                print(f"    AVISO: {item['id']} aponta para {rel}, que nao existe", file=sys.stderr)

    print(f"OK  {len(inv['items'])} itens ({t['sold_count']} vendidos)")
    print(f"    liquido {brl(t['net'])} | potencial {brl(t['potential'])} | projecao {brl(t['projection'])}")
    print(f"    site/ -> index.html + {n_items} pagina(s) de item + admin.html + data/ + copys.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
