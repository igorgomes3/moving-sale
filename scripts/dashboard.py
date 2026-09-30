#!/usr/bin/env python3
"""
Painel PRIVADO do vendedor (Moving Sale).

Design gerado no Google Stitch (tela "Desapego — Painel Privado do Vendedor",
mesmo design system da area publica). E o INVERSO da pagina publica: aqui o
Igor ve tudo — bruto, taxa por item, liquido, risco de disputa.

Onde vive: site/dashboard.html. NAO e linkado da pagina publica e carrega
`noindex,nofollow`. Ainda assim isto NAO e autenticacao de verdade — quem
souber a URL ve. Ver aviso em SEGURANCA abaixo.

SEGURANCA (importante): a fonte de verdade `data/inventory.json` esta no repo
publico do GitHub, entao os valores ja sao legiveis por qualquer pessoa que
acesse o repo. Se o Igor quiser sigilo real, o caminho e tornar o repo privado
(e o Cloudflare Pages passa a servir so o build) ou mover os dados
financeiros para fora do repo. Sinalizado no HANDOFF.
"""
from __future__ import annotations

import html
from datetime import datetime, timezone

import theme

STATUS_PILL = {
    "recebido": ("Recebido", "ok"),
    "pendente": ("A liberar", "warn"),
    "disputa": ("Em disputa", "risk"),
}

PLATFORM_LABEL = {
    "enjoei": "Enjoei",
    "facebook_marketplace": "Marketplace",
    "olx": "OLX",
    "condominio": "Condomínio",
    "outro": "Venda direta",
}

CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#f7f7f8;--card:#fff;--line:#e5e7eb;--line2:#f0f0f2;
  --txt:#111827;--dim:#6b7280;--dim2:#9ca3af;
  --accent:#e8590c;--accent-soft:#fff4ec;--accent-line:#ffd9bf;
  --ok:#15803d;--ok-bg:#dcfce7;--ok-line:#bbf7d0;
  --warn:#b45309;--warn-bg:#fef3c7;--warn-line:#fde68a;
  --risk:#b91c1c;--risk-bg:#fee2e2;--risk-line:#fecaca;
  --r:10px;--shadow:0 1px 2px rgba(17,24,39,.05);
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
}
body{background:var(--bg);color:var(--txt);font:14px/1.5 -apple-system,BlinkMacSystemFont,"Inter","Segoe UI",Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased;min-height:100vh;display:flex;flex-direction:column}
.wrap{max-width:1280px;margin:0 auto;padding:0 20px;width:100%}
a{color:inherit}

/* ---------- top bar ---------- */
.topbar{background:var(--card);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:20}
.topbar .inner{max-width:1280px;margin:0 auto;padding:13px 20px;display:flex;align-items:center;gap:14px}
.brand{font-size:18px;font-weight:750;letter-spacing:-.02em;text-decoration:none}
.brand span{color:var(--accent)}
.tagsub{font-size:13px;color:var(--dim);padding-left:13px;border-left:1px solid var(--line)}
.spacer{flex:1}
.privbadge{font-size:11px;font-weight:750;letter-spacing:.06em;text-transform:uppercase;background:var(--risk-bg);color:var(--risk);border:1px solid var(--risk-line);padding:4px 9px;border-radius:6px}
.btn{border:1px solid var(--line);background:var(--card);color:var(--txt);font:inherit;font-size:13px;font-weight:600;padding:7px 13px;border-radius:8px;cursor:pointer;text-decoration:none;display:inline-block}
.btn:hover{background:#f9fafb;border-color:#d1d5db}

/* ---------- tabs ---------- */
.tabs{background:var(--card);border-bottom:1px solid var(--line)}
.tabs .inner{max-width:1280px;margin:0 auto;padding:0 20px;display:flex;gap:2px}
.tabs a{text-decoration:none;color:var(--dim);font-size:13.5px;font-weight:600;padding:11px 14px;border-bottom:2px solid transparent}
.tabs a:hover{color:var(--txt)}
.tabs a[aria-current="page"]{color:var(--accent);border-bottom-color:var(--accent)}

/* ---------- KPIs ---------- */
main{flex:1;padding:22px 0 60px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px;margin-bottom:16px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:16px 17px;box-shadow:var(--shadow)}
.kpi .k{font-size:11.5px;font-weight:750;letter-spacing:.07em;text-transform:uppercase;color:var(--dim);margin-bottom:9px}
.kpi .v{font-size:24px;font-weight:750;letter-spacing:-.025em;font-variant-numeric:tabular-nums;font-family:var(--mono)}
.kpi .n{font-size:12.5px;color:var(--dim);margin-top:5px}
.kpi.is-ok .v{color:var(--ok)}
.kpi.is-risk .v{color:var(--risk)}
.kpi.is-warn .v{color:var(--warn)}

/* ---------- P&L ---------- */
.pl{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:17px;margin-bottom:22px;box-shadow:var(--shadow)}
.pl h2{font-size:11.5px;font-weight:750;letter-spacing:.07em;text-transform:uppercase;color:var(--dim);margin-bottom:14px}
.pl .row{display:flex;justify-content:space-between;gap:16px;padding:9px 0;font-size:14.5px;border-bottom:1px solid var(--line2)}
.pl .row .lbl{color:var(--dim)}
.pl .row .amt{font-family:var(--mono);font-variant-numeric:tabular-nums;font-weight:600;text-align:right;white-space:nowrap}
.pl .row.total{border-bottom:none;border-top:2px solid var(--txt);margin-top:6px;padding-top:13px;font-size:16.5px;font-weight:750}
.pl .row.total .lbl{color:var(--txt)}
.pl .row.total .amt{font-size:19px}

/* ---------- cards de secao ---------- */
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--shadow);overflow:hidden;margin-bottom:20px}
.card > header{padding:15px 17px;border-bottom:1px solid var(--line);display:flex;align-items:baseline;justify-content:space-between;gap:12px;flex-wrap:wrap}
.card > header h2{font-size:15.5px;font-weight:700;letter-spacing:-.01em}
.card > header .meta{font-size:12.5px;color:var(--dim)}
.card > .pad{padding:17px}

/* ---------- tabela ---------- */
.tblwrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:14px}
thead th{background:#fafafa;border-bottom:1px solid var(--line);padding:10px 12px;text-align:left;font-size:11px;font-weight:750;letter-spacing:.06em;text-transform:uppercase;color:var(--dim);white-space:nowrap}
thead th.num{text-align:right}
tbody td{padding:11px 12px;border-bottom:1px solid var(--line2);vertical-align:middle}
tbody tr:hover td{background:#fcfcfd}
td.num{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}
td.item{font-weight:600;max-width:250px}
td.plat{color:var(--dim);font-size:13px}
tfoot td{padding:12px;border-top:2px solid var(--txt);font-weight:750;font-size:14.5px}
tfoot td.num{font-family:var(--mono)}
tr.is-dispute td{background:#fffafa}
tr.is-dispute td:nth-child(5) b{color:var(--risk)}

.pill{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.03em;padding:4px 8px;border-radius:5px;white-space:nowrap}
.pill.ok{background:var(--ok-bg);color:var(--ok);border:1px solid var(--ok-line)}
.pill.warn{background:var(--warn-bg);color:var(--warn);border:1px solid var(--warn-line)}
.pill.risk{background:var(--risk-bg);color:var(--risk);border:1px solid var(--risk-line)}

/* barra de % de taxa */
.rate{display:flex;align-items:center;gap:8px;justify-content:flex-end}
.rate .bar{width:44px;height:5px;border-radius:99px;background:var(--line2);overflow:hidden;flex-shrink:0}
.rate .bar i{display:block;height:100%;border-radius:99px;background:var(--accent)}
.rate .pct{font-family:var(--mono);font-variant-numeric:tabular-nums;font-size:13px;color:var(--dim);min-width:44px;text-align:right}
.rate.hi .pct{color:var(--warn);font-weight:700}
.rate.hi .bar i{background:var(--warn)}

/* ---------- 2 colunas ---------- */
.cols{display:grid;grid-template-columns:1fr 1fr;gap:20px;align-items:start}
.todo{list-style:none}
.todo li{display:flex;gap:11px;padding:11px 0;border-bottom:1px solid var(--line2)}
.todo li:last-child{border-bottom:none}
.todo .box{width:17px;height:17px;border:1.5px solid var(--line);border-radius:5px;flex-shrink:0;margin-top:1px}
.todo .txt{font-size:14px;font-weight:600}
.todo .sub{font-size:12.5px;color:var(--dim);font-weight:400;margin-top:2px}
.todo li.urgent .box{border-color:var(--risk-line);background:var(--risk-bg)}

.selllist{list-style:none}
.selllist li{display:flex;justify-content:space-between;align-items:baseline;gap:14px;padding:12px 0;border-bottom:1px solid var(--line2)}
.selllist li:last-child{border-bottom:none}
.selllist .nm{font-size:14px;font-weight:600}
.selllist .sub{font-size:12.5px;color:var(--dim);margin-top:3px}
.selllist .pr{font-family:var(--mono);font-variant-numeric:tabular-nums;font-weight:700;font-size:15px;white-space:nowrap}
.tip{margin-top:14px;background:var(--accent-soft);border:1px solid var(--accent-line);border-radius:8px;padding:13px;font-size:13.5px;line-height:1.6}
.tip b{font-family:var(--mono)}

footer.site{border-top:1px solid var(--line);background:var(--card);padding:18px 0;color:var(--dim);font-size:12.5px;margin-top:auto}
footer.site .inner{max-width:1280px;margin:0 auto;padding:0 20px;display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap}
.lockrow{display:flex;align-items:center;gap:7px}

@media(max-width:900px){.cols{grid-template-columns:1fr}}
@media(max-width:680px){
  .wrap,.topbar .inner,.tabs .inner{padding-left:13px;padding-right:13px}
  .tagsub{display:none}
  .kpi .v{font-size:21px}
  td.item{max-width:150px}
  table{font-size:13px}
  thead th,tbody td{padding:9px 9px}
}
"""


def brl(v) -> str:
    if v is None:
        return "—"
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def neg(v) -> str:
    """Valor negativo so ganha o sinal quando existe. Zero nao e '−R$ 0,00'."""
    if not v:
        return brl(0)
    return "−" + brl(v)


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def build_pendencias(inv: dict, fees, item_fee, t: dict) -> list[dict]:
    """Deriva as pendencias dos DADOS, nao de lista chumbada.

    Cada pendencia aponta o que esta faltando de verdade no inventario.
    """
    out: list[dict] = []

    # 1. disputa aberta
    disp = [i for i in inv["items"] if i.get("payment_status") == "disputa"]
    if disp:
        names = ", ".join(i["name"] for i in disp)
        out.append({
            "urgent": True,
            "txt": f"Cobrar posicionamento sobre item em disputa",
            "sub": f"{names} — {brl(sum((i.get('sold_price') or 0) - item_fee(i, fees) for i in disp))} em risco",
        })

    # 2. liquido nao confirmado no extrato (disputa fica de fora: nao ha
    #    liquido a confirmar enquanto o valor nao for liberado)
    unconf = [i for i in inv["items"]
              if i.get("platform") == "enjoei" and i.get("net_received") is None
              and i.get("status") == "vendido"
              and i.get("payment_status") != "disputa"]
    if unconf:
        out.append({
            "urgent": False,
            "txt": f"Confirmar no extrato o líquido de {len(unconf)} venda(s)",
            "sub": "Cálculo assume modo clássico do Enjoei — validar valor recebido",
        })

    # 3. custo de entrega nao lancado
    nod = [i for i in inv["items"]
           if i.get("status") == "vendido" and i.get("delivery_cost") in (None, 0)
           and i.get("platform") in ("facebook_marketplace", "olx", "outro")]
    if nod:
        out.append({
            "urgent": False,
            "txt": f"Lançar custo de deslocamento de {len(nod)} entrega(s)",
            "sub": "Venda direta paga valor cheio: o custo é o deslocamento, e ele não aparece no líquido",
        })

    # 4. itens sem foto
    nofoto = [i for i in inv["items"] if not i.get("photos")]
    if nofoto:
        out.append({
            "urgent": False,
            "txt": f"Enviar fotos de {len(nofoto)} item(ns) sem foto",
            "sub": ", ".join(i["name"] for i in nofoto[:3]) + ("..." if len(nofoto) > 3 else ""),
        })

    # 5. campos em aberto
    oq = [(i, q) for i in inv["items"] for q in (i.get("open_questions") or [])]
    if oq:
        out.append({
            "urgent": False,
            "txt": f"Responder {len(oq)} pergunta(s) em aberto no inventário",
            "sub": "; ".join(q for _, q in oq[:2]) + ("..." if len(oq) > 2 else ""),
        })

    # 6. preço a definir
    semp = [i for i in inv["items"] if i.get("status") != "vendido" and i.get("asking_price") is None]
    if semp:
        out.append({
            "urgent": False,
            "txt": f"Definir preço de {len(semp)} item(ns) à venda",
            "sub": ", ".join(i["name"] for i in semp),
        })

    return out


def render(inv: dict, fees, t: dict, item_fee) -> str:
    items = inv["items"]
    sold = [i for i in items if i.get("status") == "vendido"]
    live = [i for i in items if i.get("status") in ("a_venda", "negociando", "reservado")]

    # linhas da tabela: maior liquido primeiro, disputa sempre visivel
    rows = sorted(sold, key=lambda i: -((i.get("sold_price") or 0) - item_fee(i, fees)))

    trs = []
    for i in rows:
        g = i.get("sold_price") or 0
        f = item_fee(i, fees)
        n = g - f - (i.get("delivery_cost") or 0)
        pct = (f / g * 100) if g else 0
        label, kind = STATUS_PILL.get(i.get("payment_status") or "", ("—", ""))
        plat = PLATFORM_LABEL.get(i.get("platform") or "", "—")
        disp = ' class="is-dispute"' if i.get("payment_status") == "disputa" else ""
        # em disputa o liquido esta em risco: fica vermelho e com nota
        liq_txt = f"<b>{brl(n)}</b>"
        trs.append(f"""      <tr{disp}>
        <td class="item">{esc(i['name'])}</td>
        <td class="plat">{esc(plat)}</td>
        <td class="num">{brl(g)}</td>
        <td class="num">{neg(f)}</td>
        <td class="num">{liq_txt}</td>
        <td class="num"><div class="rate{' hi' if pct >= 22 else ''}"><span class="bar"><i style="width:{min(pct,100):.0f}%"></i></span><span class="pct">{pct:.1f}%</span></div></td>
        <td><span class="pill {kind}">{esc(label)}</span></td>
      </tr>""")

    fee_pct = (t["fees"] / t["gross"] * 100) if t["gross"] else 0

    kpis = [
        ("Líquido recebido", t["received"], "já no bolso", "is-ok"),
        ("A liberar", t["pending"], "aguardando as plataformas", "is-warn"),
        ("Em disputa", t["dispute"], "risco de reversão", "is-risk"),
        ("Ainda à venda", t["potential"], "potencial restante", ""),
    ]
    kpi_html = "".join(
        f'<div class="kpi {cls}"><div class="k">{esc(k)}</div>'
        f'<div class="v">{brl(v)}</div><div class="n">{esc(n)}</div></div>'
        for k, v, n, cls in kpis
    )

    pend = build_pendencias(inv, fees, item_fee, t)
    pend_html = "".join(
        f'<li{" class=urgent" if p["urgent"] else ""}>'
        f'<span class="box"></span><div><div class="txt">{esc(p["txt"])}</div>'
        f'<div class="sub">{esc(p["sub"])}</div></div></li>'
        for p in pend
    ) or '<li><div class="txt">Nada pendente.</div></li>'

    sell_html = "".join(
        f'<li><div><div class="nm">{esc(i["name"])}</div>'
        f'<div class="sub">{esc(i.get("category") or "")}'
        f'{"" if i.get("photos") else " · sem foto"}</div></div>'
        f'<div class="pr">{brl(i.get("asking_price")) if i.get("asking_price") is not None else "a combinar"}</div></li>'
        for i in live
    ) or '<li><div class="nm">Nenhum item à venda.</div></li>'

    # projecao: se o que esta a venda vender pelo preco pedido, sem taxa
    proj = t["net"] + t["potential"]
    tip = ""
    if live and t["potential"]:
        tip = (f'<div class="tip"><b>Estratégia:</b> fechando os {len(live)} itens restantes '
               f'por {brl(t["potential"])} em venda direta (sem taxa), o líquido acumulado '
               f'passa de <b>{brl(t["net"])}</b> para <b>{brl(proj)}</b>.</div>')

    agora = datetime.now(timezone.utc)
    ts = agora.strftime("%d/%m/%Y %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive,nosnippet">
<meta name="referrer" content="no-referrer">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='88'%3E%F0%9F%94%92%3C/text%3E%3C/svg%3E">
<title>Painel do vendedor — {esc(theme.BRAND)}</title>
<style>{CSS}</style>
</head>
<body>

<div class="topbar">
  <div class="inner">
    <a class="brand" href="index.html">{esc(theme.BRAND)}<span>.</span></a>
    <span class="tagsub">Painel do vendedor</span>
    <span class="spacer"></span>
    <span class="privbadge">Privado</span>
    <a class="btn" href="admin.html">Editar itens</a>
    <a class="btn" href="index.html">Ver site público</a>
  </div>
</div>

<div class="tabs">
  <div class="inner">
    <a href="#resumo" aria-current="page">Resumo</a>
    <a href="#itens">Itens ({len(sold)})</a>
    <a href="#pendencias">Pendências ({len(pend)})</a>
  </div>
</div>

<div class="wrap">
<main>

  <div class="kpis">{kpi_html}</div>

  <div class="pl">
    <h2>Demonstrativo consolidado</h2>
    <div class="row"><span class="lbl">Bruto vendido</span><span class="amt">{brl(t['gross'])}</span></div>
    <div class="row"><span class="lbl">Taxas de plataforma</span><span class="amt">{neg(t['fees'])} ({fee_pct:.1f}%)</span></div>
    <div class="row"><span class="lbl">Entregas / deslocamento</span><span class="amt">{neg(t['delivery'])}</span></div>
    <div class="row total"><span class="lbl">Líquido</span><span class="amt">{brl(t['net'])}</span></div>
  </div>

  <section class="card" id="itens">
    <header>
      <h2>Itens vendidos</h2>
      <span class="meta">{len(sold)} transações · {len([i for i in sold if i.get('payment_status') == 'recebido'])} recebidos · {len([i for i in sold if i.get('payment_status') == 'pendente'])} a liberar · {len([i for i in sold if i.get('payment_status') == 'disputa'])} em disputa</span>
    </header>
    <div class="tblwrap">
      <table>
        <thead>
          <tr>
            <th>Item</th><th>Plataforma</th>
            <th class="num">Bruto</th><th class="num">Taxa</th><th class="num">Líquido</th>
            <th class="num">% taxa</th><th>Situação</th>
          </tr>
        </thead>
        <tbody>
{chr(10).join(trs)}
        </tbody>
        <tfoot>
          <tr>
            <td>Total</td><td></td>
            <td class="num">{brl(t['gross'])}</td>
            <td class="num">{neg(t['fees'])}</td>
            <td class="num">{brl(t['net'])}</td>
            <td class="num">{fee_pct:.1f}%</td>
            <td></td>
          </tr>
        </tfoot>
      </table>
    </div>
  </section>

  <div class="cols">
    <section class="card" id="pendencias">
      <header>
        <h2>Pendências</h2>
        <span class="meta">{len(pend)} a fazer</span>
      </header>
      <div class="pad"><ul class="todo">{pend_html}</ul></div>
    </section>

    <section class="card">
      <header>
        <h2>Ainda à venda</h2>
        <span class="meta">{len(live)} item(ns)</span>
      </header>
      <div class="pad">
        <ul class="selllist">{sell_html}</ul>
        {tip}
      </div>
    </section>
  </div>

</main>
</div>

<footer class="site">
  <div class="inner">
    <span class="lockrow">🔒 Dados privados — não compartilhar</span>
    <span>Atualizado {ts}</span>
  </div>
</footer>

</body>
</html>
"""
