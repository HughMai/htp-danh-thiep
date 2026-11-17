# HTP Door — danh thiếp NFC

NFC + QR business cards for Hưng Thành Phát. A tap or scan opens the person's page:
**Lưu danh bạ** (one-tap save contact), Gọi, Zalo, Facebook, Chỉ đường, Đánh giá Google, Website.

| Người | Chip + QR hold | Thẻ in |
|---|---|---|
| Mai Văn Trung — Giám đốc | `https://hughmai.github.io/htp-danh-thiep/trung/` | `print/trung.pdf` |
| Hải — KTV cửa cuốn, cửa kéo | `https://hughmai.github.io/htp-danh-thiep/hai/` | `print/hai.pdf` |
| Dương — KTV nhôm kính | `https://hughmai.github.io/htp-danh-thiep/duong/` | `print/duong.pdf` |

## Why a page, not a vCard on the chip
iPhones ignore vCard records on NFC tags; they only open URLs. A URL that links to a `.vcf`
works on every phone, and the page can be changed later (new number, new button) without
reprinting a single card.

**Never rename the repo, the GitHub account, or a slug once cards are printed** — the URL on
every chip would break. If a real domain is wanted later (e.g. `card.hungthanhphat.vn`), add it
as a GitHub Pages custom domain: GitHub then redirects the old `github.io` links to it, so printed
cards keep working.

## Edit / publish
All content lives in `PEOPLE` at the top of `build.py`.
```
PYTHONIOENCODING=utf-8 python build.py      # docs/ (website) + print/*.pdf
PYTHONIOENCODING=utf-8 python test_build.py # links, vCard format, printed QR decodes to the right URL
git commit -am "..." && git push            # GitHub Pages republishes docs/ in ~1 min
```
Close the PDFs in any viewer first; a PDF open in Foxit can't be rewritten (build says which).

## Hosting
GitHub Pages, branch `main`, folder `/docs`. Free, HTTPS, nothing to keep running.

## Printing — gửi tiệm in
- Send `print/<slug>.pdf`. Page 1 = mặt trước, page 2 = mặt sau. 94×58 mm = **90×54 mm + 2 mm
  bleed** each side; text stays ≥3 mm inside the cut.
- Ask for **"in card visit NFC"**, PVC card, chip **NTAG215**.
- Ask the shop to write each person's URL from the table above to their chips (type **URL/URI**),
  then **lock** the chips.
- Test one card per person with an iPhone and an Android **before** the shop prints the batch.
