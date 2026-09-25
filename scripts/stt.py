#!/usr/bin/env python3
"""Transcreve audio via 9Router STT. Uso: python3 stt.py <arquivo> [language]"""
import json
import mimetypes
import sys
import urllib.error
import urllib.request
import uuid
import yaml

cfg = yaml.safe_load(open("/root/.hermes/config.yaml"))
stt = cfg["stt"]["openai"]
url = stt["base_url"].rstrip("/") + "/audio/transcriptions"
key = stt["api_key"]
model = stt["model"]

path = sys.argv[1]
lang = sys.argv[2] if len(sys.argv) > 2 else "pt"

with open(path, "rb") as fh:
    data = fh.read()

boundary = "----" + uuid.uuid4().hex
parts = []
for name, value in (("model", model), ("language", lang), ("response_format", "json")):
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n")

ctype = mimetypes.guess_type(path)[0] or "audio/ogg"
filename = path.split("/")[-1]
head = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
        f"filename=\"{filename}\"\r\nContent-Type: {ctype}\r\n\r\n").encode()
body = "".join(parts).encode() + head + data + f"\r\n--{boundary}--\r\n".encode()

req = urllib.request.Request(url, data=body, method="POST", headers={
    "Authorization": f"Bearer {key}",
    "Content-Type": f"multipart/form-data; boundary={boundary}",
})
try:
    with urllib.request.urlopen(req, timeout=300) as r:
        out = json.loads(r.read().decode())
    print(out.get("text") or out)
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read().decode()[:500]}", file=sys.stderr)
    sys.exit(1)
