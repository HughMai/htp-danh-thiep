"""HTP Door — danh thiếp NFC.

One source of truth (PEOPLE below) -> everything else:
  docs/<slug>/index.html   the page an NFC tap / QR scan opens
  docs/<slug>.vcf          "Lưu danh bạ" contact file (photo = HTP door mark)
  docs/index.html          team page
  print/<slug>.pdf         card for the print shop: 2 pages (front, back), 94x58mm = 90x54 + 2mm bleed

Run:  PYTHONIOENCODING=utf-8 python build.py
Edit a person -> run again -> commit + push (GitHub Pages redeploys). The chip/QR never changes:
it holds BASE/<slug>/, so cards already handed out keep working.
"""
import base64
import html
import io
import shutil
import subprocess
import tempfile
from pathlib import Path

import segno
from PIL import Image

HERE = Path(__file__).resolve().parent
SITE = HERE / "docs"          # GitHub Pages serves main:/docs
PRINT = HERE / "print"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

BASE = "https://hughmai.github.io/htp-danh-thiep"   # GitHub Pages. Chip + QR hold BASE/<slug>/ — never change once printed.

COMPANY = "Hưng Thành Phát Door"
ADDRESS = "235–237 Võ Văn Kiệt (281 cũ), P. Bình Thủy, TP. Cần Thơ"
WEBSITE = "https://hungthanhphat.vn"
DIRECTIONS = "https://maps.google.com/?cid=12813694263297788443"
REVIEW = "https://www.google.com/maps/place//data=!4m3!3m2!1s0x31a08946f6a96a07:0xb1d3630ae8534a1b!12e1"
PRODUCTS = "Cửa cuốn · Cửa kéo · Cửa nhôm kính"

PEOPLE = [
    dict(slug="trung", name="Mai Văn Trung", title="Giám đốc",
         phone="0963021639", zalo="0913574077", facebook=None,
         contact="Mai Văn Trung (HTP Door)"),
    dict(slug="hai", name="Hải", title="Kỹ thuật viên cửa cuốn, cửa kéo",
         phone="0913080060", zalo="0913080060", facebook=None,
         contact="Hải (Cửa cuốn HTP)"),
    dict(slug="duong", name="Dương", title="Kỹ thuật viên nhôm kính",
         phone="0973695058", zalo="0973695058",
         facebook="https://www.facebook.com/sua.cua.cuon.keo",
         contact="Dương (Nhôm kính HTP)"),
]


def show(num):          # 0963021639 -> 0963 021 639
    return f"{num[:4]} {num[4:7]} {num[7:]}"


def card_url(p):      # what goes on the NFC chip and in the QR
    return f"{BASE}/{p['slug']}/"


def intl(num):          # 0963021639 -> +84963021639
    return "+84" + num[1:]


esc = html.escape

# ---------------------------------------------------------------- images
def make_images():
    logo = Image.open(HERE / "logo-src.png").convert("RGB")
    (SITE / "assets").mkdir(parents=True, exist_ok=True)
    w = 720
    logo.resize((w, round(logo.height * w / logo.width)), Image.LANCZOS).save(
        SITE / "assets" / "logo.png", optimize=True)
    # square mark = the door icon on the left of the logo, padded white
    mark = logo.crop((0, 0, 450, logo.height))
    side = max(mark.size) + 120
    sq = Image.new("RGB", (side, side), "white")
    sq.paste(mark, ((side - mark.width) // 2, (side - mark.height) // 2))
    sq.resize((256, 256), Image.LANCZOS).save(SITE / "assets" / "icon.png", optimize=True)
    buf = io.BytesIO()
    sq.resize((240, 240), Image.LANCZOS).save(buf, "JPEG", quality=82)
    return base64.b64encode(buf.getvalue()).decode()


# ---------------------------------------------------------------- vCard 3.0
def vtext(s):
    return s.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def fold(line):
    """RFC 2425 folding: <=75 octets per line, never split a UTF-8 character."""
    out, cur, size = [], "", 0
    for ch in line:
        n = len(ch.encode())
        limit = 75 if not out else 74          # continuation lines start with a space
        if size + n > limit:
            out.append(cur)
            cur, size = "", 0
        cur += ch
        size += n
    out.append(cur)
    return "\r\n ".join(out)


def vcard(p, photo_b64):
    lines = [
        "BEGIN:VCARD", "VERSION:3.0",
        f"N:;{vtext(p['contact'])};;;",
        f"FN:{vtext(p['contact'])}",
        f"ORG:{vtext(COMPANY)}",
        f"TITLE:{vtext(p['title'])}",
        f"TEL;TYPE=CELL,VOICE,pref:{intl(p['phone'])}",
    ]
    if p["zalo"] != p["phone"]:
        lines.append(f"TEL;TYPE=WORK,VOICE:{intl(p['zalo'])}")
    # Kept short on purpose: no address / website / note. Each extra field (the address adds a
    # map) pushes iPhone's "Tạo liên hệ mới" button below the fold, and people tap ✓ instead,
    # which only closes the preview. Address, website, Facebook are on the page.
    lines += [
        f"PHOTO;ENCODING=b;TYPE=JPEG:{photo_b64}",
        "END:VCARD",
    ]
    return "\r\n".join(fold(l) for l in lines) + "\r\n"


# ---------------------------------------------------------------- web page
ICONS = {
    "save": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6M22 11h-6"/>',
    "call": '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/>',
    "chat": '<path d="M21 11.5a8.4 8.4 0 0 1-9 8.4 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.2A8.4 8.4 0 0 1 12 3a8.4 8.4 0 0 1 9 8.5z"/>',
    "fb": '<path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/>',
    "pin": '<path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>',
    "star": '<path d="m12 2 3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1z"/>',
    "web": '<circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 0 1 0 20 15 15 0 0 1 0-20z"/>',
}


def icon(name):
    return (f'<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>')


FONTS_CSS = "".join(f"""
@font-face {{ font-family: "Barlow C"; font-weight: {w}; font-display: swap;
  src: url("{{root}}fonts/barlow-condensed-{w}-latin.woff2") format("woff2");
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD; }}
@font-face {{ font-family: "Barlow C"; font-weight: {w}; font-display: swap;
  src: url("{{root}}fonts/barlow-condensed-{w}-vietnamese.woff2") format("woff2");
  unicode-range: U+0102-0103, U+0110-0111, U+0128-0129, U+0168-0169, U+01A0-01A1, U+01AF-01B0, U+0300-0301, U+0303-0304, U+0308-0309, U+0323, U+0329, U+1EA0-1EF9, U+20AB; }}"""
    for w in (700, 800))

PAGE_CSS = """
:root { color-scheme: light; --brown: #4A2511; --brown2: #6B3A1C; --gold: #F5B800;
  --gold-d: #D99A00; --cream: #FBF7F1; --ink: #2A1A10; --mute: #7A6656; --line: #EADFD2; }
* { box-sizing: border-box; margin: 0; }
html { -webkit-text-size-adjust: 100%; }
body { background: var(--cream); color: var(--ink); min-height: 100vh;
  font: 16px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif; }
main { max-width: 440px; margin: 0 auto; padding: 20px 16px 32px; }
.top { background: #fff; border-radius: 18px; padding: 22px 20px 20px; text-align: center;
  box-shadow: 0 1px 2px rgba(74,37,17,.08), 0 8px 24px rgba(74,37,17,.06); }
.top img { width: 100%; max-width: 280px; height: auto; display: block; margin: 0 auto 18px; }
h1 { font: 800 34px/1.05 "Barlow C", "Arial Narrow", sans-serif; text-transform: uppercase;
  letter-spacing: .01em; color: var(--brown); }
.role { margin-top: 6px; color: var(--mute); font-weight: 600; }
.btn { display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%;
  min-height: 56px; padding: 12px 16px; border-radius: 14px; text-decoration: none;
  font: 700 19px/1.1 "Barlow C", "Arial Narrow", sans-serif; text-transform: uppercase; letter-spacing: .03em; }
.btn svg { width: 22px; height: 22px; flex: none; }
.btn small { display: block; font: 600 13px/1.2 system-ui, sans-serif; text-transform: none; letter-spacing: 0; opacity: .85; }
.hint { margin-top: 8px; padding: 10px 12px; border-radius: 10px; background: #FFF6D6;
  border: 1px solid #F5D77A; font-size: 14px; line-height: 1.4; color: var(--ink); }
.hint[hidden] { display: none; }
.save { margin-top: 16px; background: var(--gold); color: var(--brown); box-shadow: 0 2px 0 var(--gold-d); }
.stack { display: grid; gap: 10px; margin-top: 10px; }
.call { background: var(--brown); color: #fff; }
.zalo { background: #0068FF; color: #fff; }
.fb { background: #1877F2; color: #fff; }
.more { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 18px; }
.more a { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 12px 4px;
  background: #fff; border: 1px solid var(--line); border-radius: 12px; color: var(--brown);
  text-decoration: none; font-size: 13px; font-weight: 600; text-align: center; }
.more svg { width: 22px; height: 22px; }
.btn:active, .more a:active { transform: translateY(1px); }
a:focus-visible { outline: 3px solid var(--brown2); outline-offset: 2px; }
footer { margin-top: 22px; text-align: center; color: var(--mute); font-size: 13px; }
footer b { display: block; color: var(--brown); font: 700 15px/1.3 "Barlow C", sans-serif;
  text-transform: uppercase; letter-spacing: .04em; margin-bottom: 4px; }
.team { display: grid; gap: 10px; margin-top: 16px; }
.team a { display: block; background: #fff; border: 1px solid var(--line); border-radius: 14px;
  padding: 14px 16px; text-decoration: none; color: var(--ink); }
.team a b { display: block; font: 800 22px/1.1 "Barlow C", sans-serif; text-transform: uppercase; color: var(--brown); }
.team a span { color: var(--mute); font-size: 14px; }
"""


def head(title, desc, url, root):
    return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="theme-color" content="#4A2511">
<meta property="og:type" content="profile">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}/assets/logo.png">
<link rel="icon" href="{root}assets/icon.png">
<link rel="apple-touch-icon" href="{root}assets/icon.png">
<style>{FONTS_CSS.replace("{root}", root)}{PAGE_CSS}</style>
</head>"""


FOOTER = f"""<footer><b>{PRODUCTS}</b>{esc(ADDRESS)}<br>Sản xuất &amp; lắp đặt tại Cần Thơ từ 2005</footer>"""


def person_page(p):
    fb = (f'\n  <a class="btn fb" href="{esc(p["facebook"])}">{icon("fb")}<span>Facebook</span></a>'
          if p["facebook"] else "")
    zalo_note = f"<small>{show(p['zalo'])}</small>" if p["zalo"] != p["phone"] else ""
    return head(f"{p['name']} — {p['title']} · HTP Door",
                f"{p['title']} · {COMPANY} · {PRODUCTS} · Cần Thơ", card_url(p), "../") + f"""
<body>
<main>
 <section class="top">
  <img src="../assets/logo.png" alt="{COMPANY}" width="720" height="327">
  <h1>{esc(p['name'])}</h1>
  <p class="role">{esc(p['title'])}</p>
 </section>
 <a class="btn save" href="../{p['slug']}.vcf">{icon("save")}<span>Lưu vào danh bạ</span></a>
 <p class="hint" id="ios-hint" hidden>iPhone: bấm <b>Tạo liên hệ mới</b> ở cuối màn hình, rồi bấm <b>✓</b> để lưu.
  Nút ✓ ở màn hình đầu tiên chỉ là đóng lại.</p>
 <div class="stack">
  <a class="btn call" href="tel:{intl(p['phone'])}">{icon("call")}<span>Gọi {show(p['phone'])}</span></a>
  <a class="btn zalo" href="https://zalo.me/{p['zalo']}">{icon("chat")}<span>Nhắn Zalo{zalo_note}</span></a>{fb}
 </div>
 <nav class="more" aria-label="Thêm">
  <a href="{DIRECTIONS}">{icon("pin")}Chỉ đường</a>
  <a href="{REVIEW}">{icon("star")}Đánh giá Google</a>
  <a href="{WEBSITE}">{icon("web")}Website</a>
 </nav>
 {FOOTER}
</main>
<script>
if (/iP(hone|ad|od)/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1))
  document.getElementById("ios-hint").hidden = false;
</script>
</body>
</html>
"""


def team_page():
    items = "\n".join(
        f'  <a href="{p["slug"]}/"><b>{esc(p["name"])}</b><span>{esc(p["title"])} · {show(p["phone"])}</span></a>'
        for p in PEOPLE)
    return head(f"{COMPANY} — Liên hệ", f"{COMPANY} · {PRODUCTS} · Cần Thơ", BASE, "") + f"""
<body>
<main>
 <section class="top"><img src="assets/logo.png" alt="{COMPANY}" width="720" height="327"></section>
 <div class="team">
{items}
 </div>
 {FOOTER}
</main>
</body>
</html>
"""


# ---------------------------------------------------------------- print card
CARD_CSS = """
@page { size: 94mm 58mm; margin: 0; }
* { box-sizing: border-box; margin: 0; }
html, body { width: 94mm; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: "Segoe UI", Arial, sans-serif; color: #2A1A10; }
.pg { width: 94mm; height: 58mm; position: relative; overflow: hidden; page-break-after: always; }
.pg:last-child { page-break-after: auto; }
/* safe area = 2mm bleed + 3mm margin */
.front { background: #fff; }
.front .logo { position: absolute; left: 6mm; top: 6mm; width: 40mm; }
.front .who { position: absolute; left: 6mm; right: 6mm; top: 26.5mm; }
.front h1 { font: 800 17pt/1 "Barlow C", sans-serif; text-transform: uppercase; color: #4A2511; letter-spacing: .01em; }
.front .role { margin-top: 1mm; font-size: 7.6pt; font-weight: 600; color: #7A6656; }
.front .bar { position: absolute; left: 0; right: 0; bottom: 0; height: 13mm; background: #4A2511;
  display: flex; align-items: center; gap: 4mm; padding: 0 6mm 2mm; }
.front .bar .n { font: 800 15pt/1 "Barlow C", sans-serif; color: #F5B800; letter-spacing: .02em; }
.front .bar .z { font-size: 7.4pt; color: #fff; line-height: 1.2; }
.front .bar .z b { font-weight: 700; }
.front .stripe { position: absolute; right: 0; top: 0; width: 12mm; height: 45mm;
  background: repeating-linear-gradient(180deg, #F5B800 0 2.2mm, #fff 2.2mm 3mm); opacity: .9; }
.back { background: #4A2511; color: #fff; }
.back .txt { position: absolute; left: 6mm; top: 6mm; right: 33mm; }
.back .prod { font: 800 12.5pt/1.05 "Barlow C", sans-serif; text-transform: uppercase; color: #F5B800; }
.back .tag { margin-top: 1.4mm; font-size: 7pt; color: #EADFD2; }
.back .addr { position: absolute; left: 6mm; right: 33mm; bottom: 6mm; font-size: 6.6pt; line-height: 1.35; color: #fff; }
.back .addr b { color: #F5B800; font-weight: 700; }
.back .qr { position: absolute; right: 6mm; top: 6mm; width: 24mm; text-align: center; }
.back .qr .box { background: #fff; border-radius: 1.6mm; padding: 1.2mm; }
.back .qr .box svg { display: block; width: 100%; height: auto; }
.back .qr p { margin-top: 1.4mm; font-size: 6.2pt; line-height: 1.25; color: #fff; }
.back .qr p b { display: block; color: #F5B800; font: 700 8pt/1.1 "Barlow C", sans-serif; text-transform: uppercase; letter-spacing: .03em; }
.nfc { display: inline-block; width: 3.4mm; height: 3.4mm; vertical-align: -0.6mm; margin-right: .6mm; }
"""

NFC_SVG = ('<svg class="nfc" viewBox="0 0 24 24" fill="none" stroke="#F5B800" stroke-width="2.4" '
           'stroke-linecap="round"><path d="M6 8.5a5 5 0 0 1 0 7"/><path d="M10 6a9 9 0 0 1 0 12"/>'
           '<path d="M14 3.5a13 13 0 0 1 0 17"/></svg>')


def qr_svg(url):
    buf = io.BytesIO()
    segno.make(url, error="m").save(buf, kind="svg", border=0, dark="#2A1A10", xmldecl=False,
                                    svgns=True, omitsize=True)
    return buf.getvalue().decode()


def card_html(p):
    zalo_line = (f"<b>Zalo</b> {show(p['zalo'])}" if p["zalo"] != p["phone"] else "<b>Gọi · Zalo</b>")
    fonts = FONTS_CSS.replace("{root}", "../")
    return f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><title>Danh thiếp — {esc(p['name'])}</title>
<style>{fonts}{CARD_CSS}</style></head>
<body>
<section class="pg front">
 <div class="stripe"></div>
 <img class="logo" src="../docs/assets/logo.png" alt="">
 <div class="who"><h1>{esc(p['name'])}</h1><p class="role">{esc(p['title'])}</p></div>
 <div class="bar"><span class="n">{show(p['phone'])}</span><span class="z">{zalo_line}</span></div>
</section>
<section class="pg back">
 <div class="txt"><p class="prod">Cửa cuốn<br>Cửa kéo<br>Cửa nhôm kính</p>
  <p class="tag">Sản xuất &amp; lắp đặt tại Cần Thơ từ 2005</p></div>
 <p class="addr">235–237 Võ Văn Kiệt (281 cũ)<br>P. Bình Thủy, TP. Cần Thơ<br><b>hungthanhphat.vn</b></p>
 <div class="qr"><div class="box">{qr_svg(card_url(p))}</div>
  <p><b>{NFC_SVG}Chạm hoặc quét</b>để lưu số vào máy</p></div>
</section>
</body></html>
"""


def pdf(html_path, out):
    # Own profile dir: with the default one, a running Edge window swallows the job and
    # no PDF is written (silently keeping the old file). Delete first so a miss can't pass.
    out.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory() as prof:
        subprocess.run([EDGE, "--headless", "--disable-gpu", "--no-first-run", "--no-pdf-header-footer",
                        f"--user-data-dir={prof}", "--run-all-compositor-stages-before-draw",
                        "--virtual-time-budget=4000", f"--print-to-pdf={out}", html_path.as_uri()],
                       check=True, capture_output=True)
    if not out.exists():
        raise SystemExit(f"Edge wrote no PDF: {out}")


# ---------------------------------------------------------------- main
def main():
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir()
    shutil.copytree(HERE / "fonts", SITE / "fonts")
    (SITE / ".nojekyll").write_text("")
    photo = make_images()
    (SITE / "index.html").write_text(team_page(), encoding="utf-8")
    for p in PEOPLE:                                   # web first: never blocked by a PDF
        (SITE / p["slug"]).mkdir()
        (SITE / p["slug"] / "index.html").write_text(person_page(p), encoding="utf-8")
        (SITE / f"{p['slug']}.vcf").write_bytes(vcard(p, photo).encode("utf-8"))
        print(f"web {p['slug']:6} {card_url(p)}")
    PRINT.mkdir(exist_ok=True)
    locked = []
    for p in PEOPLE:
        h = PRINT / f"{p['slug']}.html"
        h.write_text(card_html(p), encoding="utf-8")
        try:
            pdf(h, PRINT / f"{p['slug']}.pdf")
            print(f"pdf {p['slug']}")
        except PermissionError:
            locked.append(p["slug"])
    if locked:
        raise SystemExit(f"PDF open in another program, close it and re-run: {', '.join(locked)}")


if __name__ == "__main__":
    main()
