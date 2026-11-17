# HTP Door — danh thiếp NFC

NFC + QR business cards for Hưng Thành Phát. A tap or scan opens the person's page at
`https://card.hungthanhphat.vn/<slug>`: **Lưu danh bạ** (one-tap save contact), Gọi, Zalo,
Facebook, Chỉ đường, Đánh giá Google, Website.

| Người | Trang | Thẻ in |
|---|---|---|
| Mai Văn Trung — Giám đốc | `/trung` | `print/trung.pdf` |
| Hải — KTV cửa cuốn, cửa kéo | `/hai` | `print/hai.pdf` |
| Dương — KTV nhôm kính | `/duong` | `print/duong.pdf` |

## Why a page, not a vCard on the chip
iPhones ignore vCard records on NFC tags; they only open URLs. A URL that links to a `.vcf`
works on every phone, and the page can be changed later (new number, new button) without
reprinting a single card. **The chip and QR hold only `card.hungthanhphat.vn/<slug>` — never
change `BASE` or a slug after printing.**

## Edit / rebuild
All content lives in `PEOPLE` at the top of `build.py`.
```
PYTHONIOENCODING=utf-8 python build.py      # site/ + print/*.pdf
PYTHONIOENCODING=utf-8 python test_build.py # links, vCard format, QR decodes to the right URL
bash deploy.sh                              # build + test + scp to Hermes
```

## Hosting (Hermes VPS)
- `/opt/htp-card/` — `site/` served by a tiny `card-site` container (caddy:2, 64 MB) on the
  `caddy_shared` network. Sets `text/vcard` on `.vcf` so iPhone shows "Tạo liên hệ mới".
- Main Caddy routes `card.hungthanhphat.vn` → `card-site:80` (`deploy/main-caddy-snippet.txt`,
  appended once). Test host before DNS: `card.187-77-133-39.sslip.io`.
- DNS: A record `card → 187.77.133.39` at tenten.vn.

## Printing — gửi tiệm in
- Send `print/<slug>.pdf`. Page 1 = mặt trước, page 2 = mặt sau. 94×58 mm = **90×54 mm + 2 mm
  bleed** each side; text stays ≥3 mm inside the cut.
- Ask for **"in card visit NFC"**, PVC card, chip **NTAG213 or NTAG215** (any phone reads them).
- Ask the shop to write this URL to each chip and **lock** it:
  - trung → `https://card.hungthanhphat.vn/trung`
  - hai → `https://card.hungthanhphat.vn/hai`
  - duong → `https://card.hungthanhphat.vn/duong`
- Test one card from each person with an iPhone and an Android **before** they print the batch.

## Open items
- Hải's Zalo assumed = his phone number (0913 080 060).
- Facebook `sua.cua.cuon.keo` is on Dương's card as given — confirm it's his, not the shop page.
- Review button uses the `!12e1` link (opens the review box); verified by Hughie on his phone.
