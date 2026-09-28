#!/usr/bin/env python3
"""
Pipeline de fotos do Moving Sale.

Le um arquivo (zip, pasta, ou lista de arquivos), casa cada imagem com um item
do inventario, normaliza (redimensiona + recomprime), gera o nome padronizado
e grava em site/img/, atualizando data/inventory.json.

Uso:
  # so mostra o casamento, nao escreve nada
  python3 scripts/photos.py --dry-run ~/fotos

  # processa de verdade (zip ou pasta)
  python3 scripts/photos.py --zip /caminho/fotos.zip
  python3 scripts/photos.py --dir /caminho/fotos

  # aponta a foto de um item a mao (vence o casamento automatico)
  python3 scripts/photos.py --set macbook-pro-16gb "MacBook Igor.jpeg"

Casamento automatico: normaliza o nome do arquivo (minusculas, sem acento,
sem espacos) e procura tokens do item. Se ficar ambiguo, NAO adivinha —
reporta e pede --set. Regra #3 do SOUL.md: nunca agir com dado nao verificado.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import unicodedata
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
# assets/ e versionado (entra no repo); build.py copia para site/img/
ASSETS_IMG = ROOT / "assets" / "img"

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".gif", ".bmp", ".tif", ".tiff"}
MAX_W = 1400
QUALITY = 82


def slug(text: str) -> str:
    """minusculas, sem acento, sem espaco, sem pontuacao."""
    t = unicodedata.normalize("NFKD", str(text))
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower()
    t = re.sub(r"[^a-z0-9]+", "", t)
    return t


# tokens que identificam cada item. Ordem importa: mais especifico primeiro.
MATCH_RULES = [
    ("macbook-pro-2010-tela-quebrada", ["macbookpro2010", "macbook2010", "macbookquebrado", "macbooktela"]),
    ("macbook-pro-16gb",              ["macbookigor", "macbook16", "macbookpro16gb", "macbook"]),
    ("controles-xbox360",             ["xbox", "joystick", "controle", "gamer", "receptor", "kitgamer"]),
    ("livros-3-unidades",             ["millennium", "livro", "trilogia"]),
    ("cafeteira-tres-coracoes",       ["cafeteira", "trescoracoes", "trescoracao", "cafeteiratre"]),
    ("casaco-creme",                  ["casaco", "sobretudo", "bege"]),
    ("jaqueta-militar-verde-m",       ["jaquetamilitar", "militar", "jaqueta"]),
    ("secadora-centrifuga",           ["secadora", "centrifuga"]),
    ("mesa-cadeira",                  ["mesa", "cadeira", "escrivaninha"]),
    ("mesinha-centro",                ["mesinha", "mesinhas", "mesacentro", "mesinha"]),
    ("maquina-lavar-mini",            ["maquinadelavar", "lavarroupa", "maquinalavar", "minilavadora"]),
    ("roupas",                        ["roupas", "roupa", "lote"]),
]


def scan_source(args) -> list[Path]:
    if args.zip:
        z = Path(args.zip).expanduser()
        if not z.exists():
            sys.exit(f"zip nao encontrado: {z}")
        dest = Path("/tmp/moving-sale-photos")
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        with zipfile.ZipFile(z) as zf:
            for m in zf.namelist():
                # protege contra path traversal
                safe = os.path.normpath(m).lstrip("/")
                if safe.startswith("..") or Path(safe).is_absolute():
                    continue
                zf.extract(m, dest)
        files = [p for p in dest.rglob("*") if p.is_file()]
    elif args.dir:
        d = Path(args.dir).expanduser()
        if not d.is_dir():
            sys.exit(f"pasta nao encontrada: {d}")
        files = [p for p in d.rglob("*") if p.is_file()]
    else:
        files = [Path(p).expanduser() for p in args.files]

    imgs = [f for f in files if f.suffix.lower() in IMG_EXT]
    # ignora lixo de sistema
    imgs = [f for f in imgs if not f.name.startswith(".") and "__MACOSX" not in str(f)]
    return sorted(imgs)


def match_item(filename: str, items: list[dict]) -> list[str]:
    """Retorna os ids candidatos, ordenados do match mais forte ao mais fraco.

    Nao basta 'a regra casou': o nome 'jaqueta-militar-verde' casa em tres regras
    ('jaquetamilitar', 'militar', 'jaqueta') da MESMA regra de item — isso nao e
    ambiguidade, e um match forte. Ambiguidade real e quando DOIS ITENS DIFERENTES
    casam. Por isso pontuamos pelo token mais longo que casou e, se o melhor
    candidato nao tiver folga sobre o segundo, devolvemos os empatados.
    """
    s = slug(Path(filename).stem)
    ids = {i["id"] for i in items}

    scores: dict[str, int] = {}
    for item_id, tokens in MATCH_RULES:
        if item_id not in ids:
            continue
        best = 0
        for tok in tokens:
            if tok in s:
                # token mais longo = match mais especifico
                best = max(best, len(tok))
        if best:
            scores[item_id] = best

    if not scores:
        return []

    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    top = ranked[0][1]
    winners = [i for i, sc in ranked if sc == top]
    if len(winners) == 1:
        return winners
    # empate real entre itens diferentes -> ambiguo de verdade
    return winners


def convert(src: Path, dest: Path) -> tuple[int, int, int]:
    """Redimensiona/recomprime. Retorna (w, h, bytes). Usa PIL se disponivel."""
    try:
        from PIL import Image, ImageOps
    except ImportError:
        shutil.copy2(src, dest.with_suffix(src.suffix))
        return (0, 0, dest.stat().st_size)

    Image.MAX_IMAGE_PIXELS = None
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)  # respeita rotacao da camera
        if im.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", im.size, (255, 255, 255))
            im = im.convert("RGBA")
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")
        if im.width > MAX_W:
            h = round(im.height * MAX_W / im.width)
            im = im.resize((MAX_W, h), Image.LANCZOS)
        dest = dest.with_suffix(".jpg")
        im.save(dest, "JPEG", quality=QUALITY, optimize=True, progressive=True)
        return (im.width, im.height, dest.stat().st_size)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", help="arquivos de imagem avulsos")
    ap.add_argument("--zip")
    ap.add_argument("--dir", dest="dir")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--set", nargs=2, action="append", metavar=("ITEM_ID", "ARQUIVO"),
                    help="forca a foto deste arquivo para este item (pode repetir)")
    args = ap.parse_args()

    inv_path = DATA / "inventory.json"
    inv = json.loads(inv_path.read_text(encoding="utf-8"))
    items = inv["items"]
    by_id = {i["id"]: i for i in items}
    ids = set(by_id)

    for item_id, _ in (args.set or []):
        if item_id not in ids:
            sys.exit(f"item_id desconhecido: {item_id}\nids validos: {', '.join(sorted(ids))}")

    imgs = scan_source(args)
    if not imgs and not args.set:
        print("Nenhuma imagem encontrada.")
        return 1
    if not imgs:
        print("Nenhuma imagem em lote; usando apenas os --set informados.\n")

    # --set: mapeia nome de arquivo -> item, com prioridade sobre o automatico
    forced_map: dict[str, str] = {}
    for item_id, fname in (args.set or []):
        forced_map[fname] = item_id
        forced_map[slug(fname)] = item_id

    plan: dict[str, list[Path]] = {}
    unmatched: list[Path] = []
    ambiguous: list[tuple[Path, list[str]]] = []

    for img in imgs:
        forced_id = forced_map.get(img.name) or forced_map.get(slug(img.name))
        if forced_id:
            plan.setdefault(forced_id, []).append(img)
            continue
        hits = match_item(img.name, items)
        if len(hits) == 1:
            plan.setdefault(hits[0], []).append(img)
        elif len(hits) > 1:
            ambiguous.append((img, hits))
        else:
            unmatched.append(img)

    # --set apontando arquivo fora da pasta/zips enviados
    for fname, item_id in forced_map.items():
        p = Path(fname).expanduser()
        if p.exists() and p.is_file():
            plan.setdefault(item_id, []).append(p)

    print(f"Imagens encontradas: {len(imgs)}\n")
    print("=" * 70)
    print("CASAMENTO")
    print("=" * 70)
    total_matched = 0
    for item in items:
        pics = plan.get(item.get("id"), [])
        if not pics:
            continue
        total_matched += len(pics)
        print(f"\n{item.get('id')}")
        print(f"  {item.get('name')}")
        for p in pics:
            print(f"    -> {p.name}")
        if len(pics) > 1:
            print(f"    ({len(pics)} fotos — a primeira vira a capa)")

    if ambiguous:
        print("\n" + "=" * 70)
        print("AMBIGUO — resolva com --set (nao vou adivinhar)")
        print("=" * 70)
        for p, hits in ambiguous:
            print(f"\n  {p.name}")
            print(f"    candidatos: {', '.join(hits)}")
            print(f"    resolva: python3 scripts/photos.py --set {hits[0]} \"{p.name}\"")

    if unmatched:
        print("\n" + "=" * 70)
        print("SEM CASAMENTO — nenhum item bateu")
        print("=" * 70)
        for p in unmatched:
            print(f"  {p.name}")

    print(f"\nTotal casado: {total_matched} foto(s) em {len(plan)} item(ns)")

    if args.dry_run:
        print("\n[DRY RUN] nada foi escrito.")
        return 0

    if not plan:
        print("\nNada para processar.")
        return 1

    ASSETS_IMG.mkdir(parents=True, exist_ok=True)
    written = 0
    for item_id, pics in plan.items():
        item = by_id[item_id]
        rels = []
        for n, src in enumerate(pics, start=1):
            suffix = "" if n == 1 else f"-{n}"
            dest = ASSETS_IMG / f"{item_id}{suffix}.jpg"
            try:
                convert(src, dest)
            except Exception as e:
                print(f"  FALHA {src.name}: {e}", file=sys.stderr)
                continue
            final = dest if dest.exists() else dest.with_suffix(src.suffix)
            rels.append(f"img/{final.name}")
            written += 1
        if rels:
            item["photos"] = rels

    inv_path.write_text(json.dumps(inv, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n{written} foto(s) processada(s) -> assets/img/")
    print(f"inventory.json atualizado com {len(plan)} item(ns).")
    print("\nAgora rode:  python3 scripts/build.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
