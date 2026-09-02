#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ライダーズイン四万十サイト｜確認用の1ファイルHTMLを作る

このリポジトリの index.html / style.css / script.js / images をひとつの
HTMLファイルにまとめる。CSSとJSは埋め込み、画像は data URI にするので、
出来たファイルは1個で完結する（オフラインでも開ける・メール添付もできる）。

さらに確認用として次を足す：
  ・合言葉ゲート（body.locked ＋ #gate）
  ・上端の黒い「確認用です」の帯
  ・robots を noindex,nofollow,noarchive に強める

使い方（このフォルダで実行）：

    python build_share.py                   既定の2か所へ出力する
    python build_share.py --check           出力せず、既存の出力との差だけ見る
    python build_share.py --password xxxx   合言葉を変える
    python build_share.py --date 2026-09-02 帯の日付を変える
    python build_share.py --out ../foo.html 出力先を自分で決める（複数指定可）
    python build_share.py --no-gate         合言葉なしで作る

出力したあとの公開手順は README.md の「デザイナー確認用の限定公開URL」を見ること。
"""

import argparse
import base64
import mimetypes
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# 既定の出力先（2か所とも同じ中身）
DEFAULT_OUTPUTS = [
    ROOT.parent / "実績ポートフォリオ_サイトコード" / "rs-ridersin-6h2n" / "index.html",
    ROOT.parent.parent / "01_プロジェクト" / "ライダーズイン四万十_サイト制作" / "共有用" / "ライダーズイン四万十_確認用.html",
]

PASSWORD = "shimanto"
REVIEW_DATE = "2026-09-02"

# 上端の帯の文言。ここを書き換えれば帯の中身が変わる
REVIEW_NOTE = """
  <div class="review-note">
    <b>確認用のたたき台です（{date}）</b> ／ 公式パンフレットのデザインをWebに展開したものです。
    <span>ロゴ・キャッチコピー・配色・書体は、パンフレットから起こしています。写真は解像度が不足しているものに「要・元データ」と印を付けています。</span>
  </div>
"""

REVIEW_CSS = """
/* ==== 確認用の帯：この共有ファイルにだけ入っています。本番には含まれません ==== */
.review-note{background:#221815;color:#fff;font-family:var(--jp-round);font-size:.8rem;
  line-height:1.7;padding:11px 20px;text-align:center;letter-spacing:.02em}
.review-note b{color:#7FD4A6;font-weight:700}
.review-note span{opacity:.72;display:inline-block}
@media(max-width:700px){.review-note{font-size:.72rem;text-align:left}}
"""

GATE_CSS = """
/* ==== 合言葉ゲート：この限定公開版にだけ入っています ==== */
body.locked > *:not(#gate){display:none!important}
#gate{display:none;min-height:100vh;align-items:center;justify-content:center;
  padding:24px;background:var(--green-mist)}
body.locked #gate{display:flex}
#gate .box{background:var(--paper);border:1px solid var(--line);padding:38px 30px;
  max-width:400px;width:100%;text-align:center;box-shadow:var(--shadow)}
#gate img{width:74px;margin:0 auto 18px}
#gate h1{font-family:var(--jp-mincho);font-weight:700;font-size:1.12rem;
  line-height:1.7;color:var(--ink);margin:0 0 6px;letter-spacing:.04em}
#gate .sub{font-family:var(--jp-round);font-size:.8rem;color:var(--ink-70);margin:0 0 22px}
#gate input{font:inherit;font-size:16px;width:100%;padding:12px 14px;
  border:1px solid var(--line);background:var(--paper-2);color:var(--ink);text-align:center;
  letter-spacing:.1em}
#gate input:focus{outline:2px solid var(--blue);outline-offset:1px}
#gate button{font-family:var(--jp-round);font-weight:700;font-size:1rem;width:100%;
  margin-top:11px;padding:13px;border:none;background:var(--green);color:#fff;cursor:pointer;
  transition:background .2s}
#gate button:hover{background:var(--green-dark)}
#gate .err{color:var(--red);font-size:.82rem;margin:12px 0 0;min-height:1.3em}
"""

GATE_HTML = """
  <div id="gate">
    <div class="box">
      <img src="{logo}" alt="">
      <h1>ライダーズイン四万十<br>ホームページ 確認用</h1>
      <p class="sub">合言葉をご入力ください</p>
      <input id="pw" type="password" autocomplete="off" inputmode="text" aria-label="合言葉">
      <button id="go" type="button">開く</button>
      <p class="err" id="err"></p>
    </div>
  </div>
"""

GATE_JS = """
<script>
var PASSWORD = "{password}";
function unlock(){{
  document.body.classList.remove('locked');
  try{{ sessionStorage.setItem('rsgate','1'); }}catch(e){{}}
}}
function tryUnlock(){{
  var v=document.getElementById('pw').value.trim().toLowerCase();
  if(v===PASSWORD.toLowerCase()){{unlock();}}
  else{{
    document.getElementById('err').textContent='合言葉が違うようです';
    document.getElementById('pw').value='';
    document.getElementById('pw').focus();
  }}
}}
try{{ if(sessionStorage.getItem('rsgate')==='1'){{document.body.classList.remove('locked');}} }}catch(e){{}}
document.getElementById('go').addEventListener('click',tryUnlock);
document.getElementById('pw').addEventListener('keydown',function(e){{
  if(e.key==='Enter'){{tryUnlock();}}
}});
if(document.body.classList.contains('locked')){{document.getElementById('pw').focus();}}
</script>
"""

# HTMLの src="./images/x" / href="..." と、CSSの url("./images/x") の両方を拾う
IMG_REF = re.compile(r'(?:(?:src|href)=(["\'])|url\(\s*(["\']?))(\.?/?images/[^"\'()\s]+)')

# 埋め込むとき、この大きさを超えるJPEGだけ作り直す（1ファイルが重くなりすぎないように）
# 元の images/ のファイルには手を触れない。作り直すのは埋め込む中身だけ。
SHRINK_OVER_BYTES = 150 * 1024
MAX_EDGE = 1600
JPEG_QUALITY = 82


def shrink_jpeg(raw):
    """大きすぎるJPEGを長辺MAX_EDGE・品質JPEG_QUALITYで作り直す。小さくならなければ元のまま"""
    try:
        from PIL import Image
    except ImportError:
        print("!! Pillow が無いので画像を縮めずに埋め込む（pip install pillow）", file=sys.stderr)
        return raw
    import io
    im = Image.open(io.BytesIO(raw))
    im = im.convert("RGB")
    if max(im.size) > MAX_EDGE:
        im.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
    out = buf.getvalue()
    return out if len(out) < len(raw) else raw


_URI_CACHE = {}


def data_uri(path):
    key = str(path)
    if key in _URI_CACHE:
        return _URI_CACHE[key]
    mime, _ = mimetypes.guess_type(path.name)
    if path.suffix.lower() == ".svg":
        mime = "image/svg+xml"
    if mime is None:
        mime = "application/octet-stream"
    raw = path.read_bytes()
    if mime == "image/jpeg" and len(raw) > SHRINK_OVER_BYTES:
        small = shrink_jpeg(raw)
        if len(small) < len(raw):
            print("  縮めた：{}  {:.0f}KB → {:.0f}KB".format(
                path.name, len(raw) / 1024, len(small) / 1024))
        raw = small
    b64 = base64.b64encode(raw).decode("ascii")
    _URI_CACHE[key] = "data:{};base64,{}".format(mime, b64)
    return _URI_CACHE[key]


def inline_images(html, missing):
    """./images/xxx の参照を data URI に置き換える"""
    def repl(m):
        ref = m.group(3)
        target = ROOT / re.sub(r"^\./", "", ref).split("?")[0]
        if not target.exists():
            missing.append(ref)
            return m.group(0)
        return m.group(0).replace(ref, data_uri(target))
    return IMG_REF.sub(repl, html)


def build(password, date):
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "style.css").read_text(encoding="utf-8")
    js = (ROOT / "script.js").read_text(encoding="utf-8")

    extra_css = REVIEW_CSS
    if password:
        extra_css += "\n  " + GATE_CSS

    # CSS を <style> に埋め込む
    html, n = re.subn(r'  <link rel="stylesheet" href="style\.css[^"]*">',
                      "  <style>\n" + css + extra_css + "\n</style>", html)
    if n != 1:
        sys.exit("!! style.css の <link> が見つからない（index.html を書き換えた？）")

    # JS を <script> に埋め込む
    html, n = re.subn(r'  <script src="script\.js"></script>',
                      "  <script>\n" + js + "\n  </script>", html)
    if n != 1:
        sys.exit("!! script.js の <script> が見つからない")

    # 検索避けを強める
    html = html.replace('<meta name="robots" content="noindex, nofollow">',
                        '<meta name="robots" content="noindex,nofollow,noarchive">')

    # 画像を data URI に
    missing = []
    html = inline_images(html, missing)
    if missing:
        print("!! 見つからない画像: " + ", ".join(sorted(set(missing))), file=sys.stderr)

    note = REVIEW_NOTE.format(date=date)

    if password:
        gate = GATE_HTML.format(logo=data_uri(ROOT / "images" / "logo-mark.svg"))
        html = html.replace("<body>\n", '<body class="locked">\n' + gate + note, 1)
        html = html.replace("</body>", GATE_JS.format(password=password) + "</body>", 1)
    else:
        html = html.replace("<body>\n", "<body>\n" + note, 1)

    return html


def main():
    ap = argparse.ArgumentParser(description="確認用の1ファイルHTMLを作る")
    ap.add_argument("--password", default=PASSWORD, help="合言葉（既定：" + PASSWORD + "）")
    ap.add_argument("--no-gate", action="store_true", help="合言葉ゲートを付けない")
    ap.add_argument("--date", default=REVIEW_DATE, help="帯に出す日付")
    ap.add_argument("--out", action="append", help="出力先（複数指定可）")
    ap.add_argument("--check", action="store_true", help="出力せず既存ファイルとの差だけ見る")
    args = ap.parse_args()

    html = build(None if args.no_gate else args.password, args.date)
    outs = [Path(o) for o in args.out] if args.out else DEFAULT_OUTPUTS

    for out in outs:
        if args.check:
            if not out.exists():
                print("[check] {} … まだ無い".format(out))
                continue
            old = out.read_text(encoding="utf-8")
            print("[check] {}\n        {}（既存 {:,} 字 / 今回 {:,} 字）".format(
                out, "差なし" if old == html else "差あり", len(old), len(html)))
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        print("書き出した：{}  {:.2f} MB".format(out, out.stat().st_size / 1024 / 1024))

    if not args.check:
        print("\n公開する（URLは変わらない・反映まで1〜3分）：")
        print('  cd "G:/マイドライブ/2nd-Brain/01_制作したWebサイト/実績ポートフォリオ_サイトコード"'
              ' && git add rs-ridersin-6h2n && git commit -m "ライダーズ確認用を更新" && git push')


if __name__ == "__main__":
    main()
