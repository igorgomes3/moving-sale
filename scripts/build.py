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

import dashboard
import theme

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
.toolbar{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:22px 0 20px}
.toolbar input[type=search]{flex:1;min-width:200px;background:var(--card);border:1px solid var(--line);border-radius:10px;color:var(--txt);padding:11px 14px;font:inherit;font-size:15px}
.toolbar input[type=search]:focus{outline:none;border-color:var(--accent)}
.toolbar input[type=search]::placeholder{color:var(--dim)}
.filters{display:flex;gap:8px;flex-wrap:wrap}
.filters button{
  background:var(--card);color:var(--dim);border:1px solid var(--line);border-radius:999px;
  padding:9px 17px;font-size:14px;font-weight:600;cursor:pointer;font-family:inherit;transition:.15s
}
.filters button:hover{color:var(--txt);border-color:#3a4250}
.filters button[aria-pressed="true"]{background:var(--accent);color:#06240f;border-color:var(--accent)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(258px,1fr));gap:18px;align-items:stretch}
.grid:has(.card:only-child){grid-template-columns:minmax(258px,340px)}
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
.cta:hover{background:var(--accent2);text-decoration:none}
.cta.ghost{background:transparent;border:1px solid var(--line);color:var(--dim);cursor:default}
.cta.ghost:hover{background:transparent}
.cta.soldout{background:var(--card2);border:1px solid var(--line);color:var(--dim);cursor:default;margin-top:4px}
.cta.soldout:hover{background:var(--card2)}
.card{position:relative;display:flex;flex-direction:column;text-decoration:none;color:inherit}
.card .name{color:var(--txt)}
.card .price .now{color:var(--txt)}
.card:hover .name{color:var(--accent)}
.mais{position:absolute;left:0;right:0;bottom:0;background:linear-gradient(to top,var(--card) 65%,transparent);color:var(--dim);text-align:center;font-size:13px;font-weight:600;padding:26px 0 11px;opacity:0;transition:.18s;pointer-events:none}
.card:hover .mais{opacity:1}
.card.sold .name{color:var(--dim)}
.card.sold .cond,.card.sold .specs{opacity:.55}
.empty{text-align:center;color:var(--dim);padding:70px 20px}
footer{margin-top:56px;padding-top:24px;border-top:1px solid var(--line);color:var(--dim);font-size:13.5px;display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}
footer a{color:var(--dim)}
@media(max-width:520px){.wrap{padding:22px 14px 60px}.grid{grid-template-columns:1fr 1fr;gap:12px}.name{font-size:14.5px}.price .now{font-size:18px}.body{padding:12px;gap:7px}.stats{grid-template-columns:1fr 1fr}}
"""

JS = """
const ITEMS = __ITEMS__;
const META  = __META__;
const WA    = META.whatsapp;
let filter = 'a_venda';

function brl(v){ return v==null ? '—' : 'R$ ' + v.toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2}); }
function esc(s){ return String(s==null?'':s).replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

function render(){
  const grid = document.getElementById('grid');
  const q = (document.getElementById('busca').value || '').trim().toLowerCase();
  const list = ITEMS.filter(i => {
    if (filter === 'a_venda' && !(i.status === 'a_venda' || i.status === 'negociando' || i.status === 'reservado')) return false;
    if (filter !== 'a_venda' && filter !== 'todos' && i.status !== filter) return false;
    if (q && !(i.name + ' ' + (i.category||'')).toLowerCase().includes(q)) return false;
    return true;
  });
  if (!list.length){
    grid.innerHTML = '<div class="empty">Nenhum item encontrado.</div>';
  } else {
    grid.innerHTML = list.map(card).join('');
  }
  const aVenda = ITEMS.filter(i => i.status === 'a_venda' || i.status === 'negociando' || i.status === 'reservado').length;
  document.getElementById('contagem').textContent = aVenda + ' ' + (aVenda === 1 ? 'item disponível' : 'itens disponíveis');
}

function card(i){
  const sold = i.status === 'vendido';

  // Item vendido: nunca expor o valor. Nao e dado publico.
  let priceHtml = '';
  if (!sold){
    const p = i.asking_price;
    priceHtml = p != null
      ? '<div class="price"><span class="now">' + brl(p) + '</span><span class="lbl">' + (i.status === 'negociando' ? 'em negociação' : 'à vista') + '</span></div>'
      : '<div class="price"><span class="undef">Preço a combinar</span></div>';
  }

  const photo = (i.photos && i.photos.length)
    ? '<img src="' + esc(i.photos[0]) + '" alt="' + esc(i.name) + '" loading="lazy">'
    : '<span class="nofoto">sem foto</span>';

  // CTA padrao de marketplace: so "Ver detalhes". Sem WhatsApp no card —
  // o contato acontece na pagina do item, como em qualquer marketplace.
  const cta = sold
    ? ''
    : '<span class="cta">Ver detalhes</span>';

  const specs = i.specs ? '<div class="specs">' + Object.values(i.specs).map(esc).join(' · ') + '</div>' : '';
  const note = (!sold && i.notes) ? '<div class="notes">' + esc(i.notes) + '</div>' : '';

  const inner = '<div class="ph">' + photo
    + '<div class="badges"><span class="badge b-' + i.status + '">' + esc(i.status_label) + '</span></div></div>'
    + '<div class="body">'
    +   '<div class="cat">' + esc(i.category) + (i.qty && i.qty > 1 ? ' · ' + i.qty + ' itens' : '') + '</div>'
    +   '<div class="name">' + esc(i.name) + '</div>'
    +   (i.condition ? '<div class="cond">' + esc(i.condition) + '</div>' : '')
    +   specs + note
    +   priceHtml
    +   cta
    + '</div><span class="mais">Ver detalhes</span>';

  return '<a class="card ' + (sold?'sold':'') + '" href="item/' + esc(i.id) + '.html" '
    + 'data-status="' + i.status + '" aria-label="' + esc(i.name) + '">' + inner + '</a>';
}

document.getElementById('busca').addEventListener('input', render);

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

    # NOTA: a pagina publica NAO mostra nenhum total financeiro.
    # Faturamento, taxas, disputa e liquido sao dados privados do Igor —
    # visiveis apenas no /admin.html. Ver HANDOFF §9.

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E%F0%9F%8F%B7%EF%B8%8F%3C/text%3E%3C/svg%3E">
<title>{esc(meta.get('title','Desapego'))}</title>
<meta name="description" content="{esc(meta.get('subtitle',''))}">
<meta property="og:title" content="{esc(meta.get('title','Desapego'))}">
<meta property="og:description" content="{esc(meta.get('subtitle',''))}">
<meta name="twitter:card" content="summary_large_image">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>{esc(meta.get('title','Desapego'))}</h1>
    <p class="sub">{esc(meta.get('subtitle',''))}</p>
  </header>
  <div class="toolbar">
    <input type="search" id="busca" placeholder="Buscar item..." aria-label="Buscar item">
    <div class="filters">
      <button data-f="a_venda" aria-pressed="true">À venda</button>
      <button data-f="todos" aria-pressed="false">Todos</button>
      <button data-f="vendido" aria-pressed="false">Vendidos</button>
    </div>
  </div>
  <div class="grid" id="grid"></div>
  <footer>
    <span id="contagem"></span>
    <span>Retirada combinada com o vendedor</span>
  </footer>
</div>
<script>
{JS.replace('__ITEMS__', json.dumps(items, ensure_ascii=False, indent=None)).replace('__META__', json.dumps(meta, ensure_ascii=False))}
</script>
</body>
</html>
"""


def build_item_pages(inv: dict, meta: dict) -> int:
    """Gera site/item/<id>.html via theme.render_item.

    Toda a apresentacao publica vive em theme.py; aqui so orquestramos.
    """
    out_dir = SITE / "item"
    out_dir.mkdir(parents=True, exist_ok=True)
    wa = meta.get("whatsapp") or ""
    count = 0
    for item in inv["items"]:
        page = theme.render_item(item, meta, len(inv["items"]), wa)
        (out_dir / f"{item['id']}.html").write_text(page, encoding="utf-8")
        count += 1
    return count


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


def public_items(inv: dict, t: dict) -> list[dict]:
    """Prepara os itens para a camada publica (theme.py).

    ALLOWLIST explicita: so estes campos saem daqui. Tudo o que nao esta na
    lista (notes internas, plataforma, taxas, disputa, open_questions,
    market_research, net_received...) NUNCA chega ao HTML publico — nem no
    JSON embutido, que e legivel por qualquer visitante.

    Regra do Igor (26/09): dado financeiro e privado. Preco de item vendido
    nao aparece. Ver HANDOFF secao 9.
    """
    CAMPOS = (
        "id", "name", "category", "qty", "condition", "asking_price",
        "status", "photos", "specs", "public_notes",
    )
    out = []
    for n, item in enumerate(inv["items"]):
        d = {k: item.get(k) for k in CAMPOS}
        d["status_label"] = STATUS_LABEL.get(item.get("status"), item.get("status"))
        d["price_html"] = theme.public_price(item)
        c = (item.get("condition") or "").lower()
        d["condition_group"] = "novo" if "novo" in c and "usad" not in c else "usado"
        d["_p"] = None if item.get("status") == "vendido" else item.get("asking_price")
        d["_i"] = n
        out.append(d)
    return out


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

    pub_items = public_items(inv, t)
    (SITE / "index.html").write_text(theme.render_index(pub_items, inv["meta"]), encoding="utf-8")
    n_items = build_item_pages(inv, inv["meta"])
    (SITE / "data" / "inventory.json").write_text(json.dumps(inv, ensure_ascii=False, indent=2), encoding="utf-8")
    (SITE / "data" / "fees.json").write_text(json.dumps(fees, ensure_ascii=False, indent=2), encoding="utf-8")
    (SITE / "copys.md").write_text(build_copys(inv), encoding="utf-8")
    (SITE / "resumo.md").write_text(build_resumo(inv, fees, t), encoding="utf-8")

    # painel privado do vendedor (nao linkado do publico)
    (SITE / "dashboard.html").write_text(
        dashboard.render(inv, fees, t, item_fee), encoding="utf-8")

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
