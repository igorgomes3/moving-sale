#!/usr/bin/env python3
"""Calculadora de liquido/arrecadacao do Moving Sale.

Le data/inventory.json + data/fees.json e calcula, por item:
  - bruto
  - taxa da plataforma (comissao % + tarifa fixa por faixa)
  - custo de entrega/deslocamento
  - liquido real

IMPORTANTE: a taxa do Enjoei NAO e um percentual flat. E comissao% + tarifa fixa
escalonada por faixa de preco. Por isso a taxa efetiva varia item a item.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INVENTORY = ROOT / "data" / "inventory.json"
FEES = ROOT / "data" / "fees.json"

SOLD = {"vendido"}
PENDING_PAYMENT = {"pendente", "disputa"}


def load(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def fixed_fee(bands: list[dict], price: float) -> float:
    """Tarifa fixa da faixa em que o preco cai."""
    for band in bands:
        ceiling = band["max_price"]
        if ceiling is None or price <= ceiling:
            return float(band["fixed"])
    return 0.0


def platform_fee(item: dict, fees: dict) -> tuple[float, str]:
    """Retorna (valor_da_taxa, explicacao)."""
    gross = item.get("sold_price")
    if gross is None:
        return 0.0, "sem venda"

    platform = item.get("platform")
    if platform != "enjoei":
        return 0.0, "sem comissao"

    mode = item.get("enjoei_mode") or "classico"
    spec = fees["enjoei"]["modes"][mode]
    commission = gross * spec["commission_pct"] / 100.0
    fixed = fixed_fee(spec["fixed_fee_bands"], gross) if spec["fixed_fee_bands"] else 0.0
    total = commission + fixed
    label = f"{spec['commission_pct']:.0f}% ({commission:.2f}) + fixa ({fixed:.2f})"
    return total, label


def net_of(item: dict, fees: dict) -> dict:
    gross = item.get("sold_price") or 0.0
    fee, fee_label = platform_fee(item, fees)

    # Se o Igor ja informou o liquido recebido, ele vence o calculo teorico.
    informed = item.get("net_received")
    if informed is not None:
        fee = gross - informed
        fee_label = f"informado (bruto {gross:.2f} - liquido {informed:.2f})"

    delivery = item.get("delivery_cost") or 0.0
    net = gross - fee - delivery
    return {
        "gross": gross,
        "fee": fee,
        "fee_label": fee_label,
        "delivery": delivery,
        "net": net,
        "fee_pct_effective": (fee / gross * 100.0) if gross else 0.0,
    }


def main() -> int:
    inv = load(INVENTORY)
    fees = load(FEES)
    items = inv["items"]

    rows = []
    for item in items:
        calc = net_of(item, fees)
        rows.append((item, calc))

    sold = [(i, c) for i, c in rows if i["status"] in SOLD]

    gross_sold = sum(c["gross"] for _, c in sold)
    fees_sold = sum(c["fee"] for _, c in sold)
    delivery_sold = sum(c["delivery"] for _, c in sold)
    net_sold = sum(c["net"] for _, c in sold)

    received = sum(c["net"] for i, c in sold if i.get("payment_status") == "recebido")
    pending = sum(c["net"] for i, c in sold if i.get("payment_status") == "pendente")
    dispute = sum(c["net"] for i, c in sold if i.get("payment_status") == "disputa")

    print("=" * 78)
    print("VENDIDOS")
    print("=" * 78)
    for item, c in sold:
        flag = ""
        if item.get("payment_status") == "disputa":
            flag = "  [DISPUTA]"
        elif item.get("payment_status") == "pendente":
            flag = "  [a liberar]"
        print(f"\n{item['name']}{flag}")
        print(f"  bruto          R$ {c['gross']:>10,.2f}")
        print(f"  taxa           R$ {c['fee']:>10,.2f}   ({c['fee_label']})")
        if c["delivery"]:
            print(f"  entrega        R$ {c['delivery']:>10,.2f}")
        print(f"  LIQUIDO        R$ {c['net']:>10,.2f}   (taxa efetiva {c['fee_pct_effective']:.1f}%)")
        if item.get("net_received_confirmed") is False:
            print("  ! liquido informado de memoria - CONFIRMAR no extrato")

    print()
    print("=" * 78)
    print("TOTAIS")
    print("=" * 78)
    print(f"  vendido bruto            R$ {gross_sold:>10,.2f}")
    print(f"  taxas de plataforma      R$ {fees_sold:>10,.2f}")
    print(f"  entregas/deslocamento    R$ {delivery_sold:>10,.2f}")
    print(f"  LIQUIDO TOTAL            R$ {net_sold:>10,.2f}")
    print()
    print(f"  ja recebido (Pix)        R$ {received:>10,.2f}")
    print(f"  a liberar                R$ {pending:>10,.2f}")
    print(f"  em disputa (risco)       R$ {dispute:>10,.2f}")

    print()
    print("=" * 78)
    print("A VENDA / NEGOCIANDO (potencial)")
    print("=" * 78)
    potential = 0.0
    for item, _ in rows:
        if item["status"] in ("a_venda", "negociando", "reservado"):
            asking = item.get("asking_price")
            asking_txt = f"R$ {asking:,.2f}" if asking is not None else "preco a definir"
            print(f"  [{item['status']:>10}] {item['name']:<48} {asking_txt}")
            if asking:
                potential += asking
    print()
    print(f"  potencial de arrecadacao R$ {potential:>10,.2f}")
    print(f"  PROJECAO total           R$ {net_sold + potential:>10,.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
