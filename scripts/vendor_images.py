#!/usr/bin/env python3
"""Download Slow Glow's currently referenced Yandex image files into this repo.

Run from the repository root. Fail without touching index.html if any image
cannot be retrieved and verified as an image. This keeps the live site safe.
"""
from __future__ import annotations

import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
HTML = ROOT / "index.html"
ASSETS = ROOT / "assets"

IMAGES = [
    ("studio-logo", "https://avatars.mds.yandex.net/get-altay/16431464/2a0000019a2784d58f5fe970b7699cde50dd/S"),
    ("work-manicure-1", "https://avatars.mds.yandex.net/get-altay/19392709/2a0000019e7e50fe5a2710f78ffe4de46343/XXL_height"),
    ("work-manicure-2", "https://avatars.mds.yandex.net/get-altay/19708557/2a0000019e7e50f53abffed7e4940963fe35/XXL_height"),
    ("work-manicure-3", "https://avatars.mds.yandex.net/get-altay/18148618/2a0000019d305541dc439ddfb444e8c31bda/XXL_height"),
    ("work-manicure-4", "https://avatars.mds.yandex.net/get-altay/19707167/2a0000019d305527f7e87e29863f183063e0/XXL_height"),
    ("studio-interior-1", "https://avatars.mds.yandex.net/get-altay/18396981/2a0000019aa615603fd6f6e7043fb7fbce9d/XXL_height"),
    ("studio-interior-2", "https://avatars.mds.yandex.net/get-altay/16789805/2a0000019aa61564c63ae925bfa27cdf687d/XXL_height"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "image/jpeg,image/png,image/webp,image/avif;q=0.5,*/*;q=0.1",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.7",
    "Referer": "https://yandex.ru/",
}

def image_ext(blob: bytes) -> str | None:
    if len(blob) < 500:
        return None
    if blob[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if blob[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
        return ".webp"
    if blob[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    if blob[4:12] in (b"ftypavif", b"ftypavis"):
        return ".avif"
    return None

def candidates(original: str):
    yield original
    if original.endswith("/XXL_height"):
        for size in ("XXL", "L", "M", "S"):
            yield original.rsplit("/", 1)[0] + "/" + size
    # A proxy can resolve CDN restrictions without requiring images in users' browsers.
    # It is only used at build time; the final site references local assets exclusively.
    from urllib.parse import quote
    for size in ("XXL_height", "L", "M"):
        base = original.rsplit("/", 1)[0] if original.endswith("/XXL_height") else original.rsplit("/", 1)[0]
        suffix = size if original.endswith("/XXL_height") else "S"
        remote = base + "/" + suffix
        yield "https://wsrv.nl/?url=" + quote(remote, safe="") + "&output=jpg"

def download(url: str, name: str) -> tuple[bytes, str]:
    errors = []
    for idx, attempt in enumerate(dict.fromkeys(candidates(url)), 1):
        try:
            req = urllib.request.Request(attempt, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=22) as response:
                body = response.read(15_000_000)
                mimetype = response.headers.get("Content-Type", "")
            ext = image_ext(body)
            if ext is None:
                raise ValueError(f"not a supported image: content-type={mimetype} bytes={len(body)}")
            print(f"OK: {name}: {len(body)} bytes, {ext} (try {idx})", flush=True)
            return body, ext
        except Exception as exc:
            msg = f"try {idx}: {type(exc).__name__}: {str(exc)[:120]}"
            print(f"WARN: {name}: {msg}", flush=True)
            errors.append(msg)
            time.sleep(0.4)
    raise RuntimeError(f"Cannot mirror {name}: {'; '.join(errors)}")

def main() -> None:
    old_html = HTML.read_text(encoding="utf-8")
    downloaded: list[tuple[str, bytes, str, str]] = []
    for name, url in IMAGES:
        if url not in old_html:
            raise RuntimeError(f"Missing source URL in HTML: {name}")
        data, ext = download(url, name)
        downloaded.append((name, data, ext, url))
    # Commit-ready writes only after every source succeeds.
    ASSETS.mkdir(exist_ok=True)
    new_html = old_html
    for name, data, ext, url in downloaded:
        dest = ASSETS / (name + ext)
        dest.write_bytes(data)
        new_html = new_html.replace(url, f"assets/{name}{ext}")
    if "src=\"https://avatars.mds.yandex.net" in new_html:
        raise RuntimeError("Some external Yandex image references remain")
    HTML.write_text(new_html, encoding="utf-8")
    print(f"READY: {len(downloaded)} images stored locally; all original Yandex image src references replaced", flush=True)

if __name__ == "__main__":
    main()
