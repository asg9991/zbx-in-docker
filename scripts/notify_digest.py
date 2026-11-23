#!/usr/bin/env python3
"""Envía el digest a Discord, Slack o Telegram (N4).

No decide nada: toma el mismo digest que genera scripts/digest.py y lo manda.
Sin destinatario configurado, imprime (dry-run) y no falla.

Env:
  DIGEST_WEBHOOK_URL   webhook de Discord o Slack
  DIGEST_FORMATO       discord (default) | slack
  TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
Uso:
  python3 scripts/notify_digest.py --dry-run
  python3 scripts/notify_digest.py --solo-alertas   # solo si hay crítico/degradado
"""

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest_markdown() -> str:
    r = subprocess.run([sys.executable, str(ROOT / "scripts/digest.py")],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        sys.exit(f"ERROR generando digest: {r.stderr[:200]}")
    return r.stdout.strip()


def main() -> int:
    args = sys.argv[1:]
    dry = "--dry-run" in args
    solo_alertas = "--solo-alertas" in args
    texto = digest_markdown()

    if solo_alertas and "CRITICO" not in texto and "DEGRADADO" not in texto:
        print("sin servicios afectados: no se envía")
        return 0

    if len(texto) > 3500:
        texto = texto[:3400] + "\n…(truncado)"

    webhook = os.getenv("DIGEST_WEBHOOK_URL", "").strip()
    formato = os.getenv("DIGEST_FORMATO", "discord").strip()
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    if formato == "slack":
        payload = {"text": "```\n" + texto + "\n```"}
    else:
        payload = {"content": "```\n" + texto + "\n```"}

    if dry or (not webhook and not (tg_token and tg_chat)):
        print("--- destino: (ninguno configurado) ---")
        print(json.dumps(payload, ensure_ascii=False)[:1200])
        return 0

    if webhook:
        req = urllib.request.Request(webhook, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            print(f"webhook: {r.status}")
        return 0

    url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
    body = {"chat_id": tg_chat, "text": texto[:4000], "disable_web_page_preview": True}
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        print(f"telegram: {r.status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
