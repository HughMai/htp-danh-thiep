"""Smoke test: run after build.py.  python test_build.py
Checks every person's page, contact file, and that the printed QR decodes to the right URL."""
import re
import sys
from pathlib import Path

import cv2
import fitz
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from build import BASE, PEOPLE, PRINT, SITE, intl  # noqa: E402

fails = []


def check(ok, msg):
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok:
        fails.append(msg)


for p in PEOPLE:
    s = p["slug"]
    page = (SITE / s / "index.html").read_text(encoding="utf-8")
    check(f'href="tel:{intl(p["phone"])}"' in page, f"{s}: call button -> {intl(p['phone'])}")
    check(f'href="https://zalo.me/{p["zalo"]}"' in page, f"{s}: zalo button -> {p['zalo']}")
    check(f'href="../{s}.vcf"' in page, f"{s}: save-contact button -> {s}.vcf")
    check((p["facebook"] or "") in page and (p["facebook"] is not None) == ("Facebook" in page),
          f"{s}: facebook button only when set")
    for ref in re.findall(r'(?:src|href)="(\.\./[^"]+)"', page):
        check((SITE / s / ref).resolve().exists(), f"{s}: local link {ref} exists")

    raw = (SITE / f"{s}.vcf").read_bytes()
    text = raw.decode("utf-8")
    lines = raw.split(b"\r\n")
    check(text.startswith("BEGIN:VCARD\r\nVERSION:3.0\r\n") and text.endswith("END:VCARD\r\n"), f"{s}: vcf framing + CRLF")
    check(all(len(l) <= 75 for l in lines), f"{s}: vcf lines <= 75 octets")
    unfolded = text.replace("\r\n ", "")
    check(f"TEL;TYPE=CELL,VOICE,pref:{intl(p['phone'])}" in unfolded, f"{s}: vcf main phone")
    check(f"FN:{p['contact']}" in unfolded, f"{s}: vcf name '{p['contact']}'")
    check("PHOTO;ENCODING=b;TYPE=JPEG:/9j/" in unfolded, f"{s}: vcf photo")

    doc = fitz.open(PRINT / f"{s}.pdf")
    size = [round(v / 72 * 25.4) for v in (doc[0].rect.width, doc[0].rect.height)]
    check(len(doc) == 2 and size == [94, 58], f"{s}: card pdf 2 pages 94x58mm (got {len(doc)}, {size})")
    pix = doc[1].get_pixmap(dpi=400)
    img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3]
    found, _, _ = cv2.QRCodeDetector().detectAndDecode(np.ascontiguousarray(img))
    check(found == f"{BASE}/{s}", f"{s}: printed QR decodes to {BASE}/{s} (got {found!r})")

print(f"\n{'ALL PASS' if not fails else f'{len(fails)} FAILED'}")
sys.exit(1 if fails else 0)
