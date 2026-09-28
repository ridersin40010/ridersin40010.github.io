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
import datetime
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# 既定の出力先（2か所とも同じ中身＝正規の PDF貼り付け版）
# 2026-09-28：既定を rs-ridersin-6h2n から rs-ridersin-p-8k2d に変えた。
# 6h2n（縦長版）と w-3m7q（横長版）は 9/15 で更新を止めた版なので、
# 素で走らせたときに古い版だけが書き換わる事故を防ぐため。
DEFAULT_OUTPUTS = [
    ROOT.parent / "実績ポートフォリオ_サイトコード" / "rs-ridersin-p-8k2d" / "index.html",
    ROOT.parent.parent / "01_プロジェクト" / "ライダーズイン四万十_サイト制作" / "共有用" / "ライダーズイン四万十_確認用.html",
]

PASSWORD = "shimanto"
# 帯に出す日付。既定はビルドした日（--date で上書きできる）
REVIEW_DATE = datetime.date.today().isoformat()

# 上端の帯の文言。ここを書き換えれば帯の中身が変わる
REVIEW_NOTE = """
  <div class="review-note">
    <b>確認用のたたき台です（{date}）</b> ／ 公式パンフレットのデザインをWebに展開したものです。
    <span>ロゴ・キャッチコピー・配色・書体は、パンフレットから起こしています。写真は解像度が不足しているものに「要・元データ」と印を付けています。</span>
  </div>
"""

# ── 大村さん案（横長）の差分CSS ────────────────────────────────
# 本体の style.css は触らず、ビルド時にこれを後ろに足して上書きする。
# 値はすべて PC 側（＝カンプ）の指定をそのまま持ってきたもの。
HERO_WIDE_CSS = """
/* ==== 大村さん案：スマホでもPDF・PCと同じ横長のサイズ感にする ====
   既定の版（スマホは縦長3:4）との比較用。本体CSSは変更していない。
   位置の数値は style.css の :root 変数をそのまま使うので、
   カンプに合わせて直すときは style.css だけ直せばこちらにも効く */
@media (max-width: 700px) {
  .hero  { aspect-ratio: 1280 / 860; }
  .hero2 { aspect-ratio: 1280 / 845; }

  .hero-rs {
    left: var(--hero-rs-left);
    top: var(--hero-rs-top);
    transform: none;
    font-size: var(--hero-rs-size);
  }

  .hero-roman {
    left: 0;
    width: var(--hero-roman-width);
    top: var(--hero-roman-top);
  }

  .hero-roman .l1,
  .hero-roman .l3 { font-size: 3.67vw; }
  .hero-roman .l2 { font-size: 2.66vw; }

  .hero2-catch {
    top: var(--hero-catch-top);
    /* カンプの比率どおりだと375pxで8.8pxになり読めないので、
       下限だけ12.8pxで止めている。ここも合わせるかは大村さんに要確認 */
    font-size: clamp(.8rem, 2.34vw, 1.88rem);
    letter-spacing: .27em;
    text-indent: .135em;
  }
}
"""

HERO_WIDE_NOTE = """
  <div class="review-note">
    <b>確認用｜横長版（{date}）</b> ／ スマホでもPDF・PCと同じ横長のサイズ感にした版です。
    <span>ヒーローの比率・RSロゴ・キャッチの位置を、すべてPC側（＝パンフのカンプ）の値に揃えています。もう一方のURLは、スマホでは縦長に切った版です。</span>
  </div>
"""

# ── 大村さん案②：カンプPDFのヒーロー部分をそのまま画像で貼る比較版 ─────────
# images/hero-pdf.jpg は 大村さんカンプ_2026-09-08.pdf の y3〜1506（ヒーロー①②と
# 境目のぼかし込み）を書き出したもの。本体の index.html / style.css は触らない。
HERO_PDF_HTML = """  <!-- ============ ヒーロー（カンプPDFをそのまま画像で貼った比較版） ============ -->
  <section class="hero-pdf" id="hero">
    <img src="./images/hero-pdf.jpg" width="1362" height="1600"
      alt="四万十川の空撮と、川沿いに並ぶライダーズイン四万十のキャビン">
    <!-- 画像の中の文字を、検索と読み上げのために本物の文字でも置いておく（画面には出ない） -->
    <div class="vh">
      <h1>ライダーズイン四万十　RIDER’S INN SHIMANTO</h1>
      <p>THE SHIMANTO RIVER IN KOCHI, JAPAN</p>
      <p>四万十川のほとりで泊まる　四万十川と一緒に眠る</p>
    </div>
  </section>
"""

HERO_PDF_CSS = """
/* ==== 大村さん案②：ヒーローはカンプPDFをそのまま画像で貼る ==== */
.hero-pdf { width: 100%; background: #fff; }
.hero-pdf img { display: block; width: 100%; height: auto; }
.vh { position: absolute !important; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0; }
"""

HERO_PDF_NOTE = """
  <div class="review-note">
    <b>確認用｜PDF貼り付け版（{date}）</b> ／ ヒーロー部分に、大村さんのカンプPDFをそのまま画像で貼った版です。
    <span>RS・英字・キャッチ・境目のぼかしまでカンプと同じです。画像なので、スマホでは文字がそのまま縮みます。</span>
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

# 解像度が足りない写真に出す赤い札。確認用ビルドにだけ入れる（本番には出ない）。
# 目印の class（.ph.lowres）は本体 index.html 側に付いたままでよい。
REVIEW_LOWRES_CSS = """
/* ==== 「要・元データ」の札：この確認用ファイルにだけ入っています ==== */
.ph.lowres::after{content:"要・元データ";position:absolute;top:9px;left:9px;
  font-family:var(--jp-sans);font-size:.62rem;font-weight:500;letter-spacing:.04em;
  color:var(--red);background:rgba(255,255,255,.93);border:1px dashed var(--red);
  border-radius:4px;padding:2px 7px}
.ph.lowres img{filter:saturate(.9)}
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
# 2026-09-28：元データに差し替えて1ファイルが6.6MBになったので、埋め込む側だけ1400に下げた。
# スマホで開く確認用ファイルなので、画面の横幅（〜430pt×3倍＝約1290px）に足りていればよい。
# サイト本体の images/ は大きいまま。
MAX_EDGE = 1400
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


def build(password, date, hero_wide=False, hero_pdf=False):
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "style.css").read_text(encoding="utf-8")
    js = (ROOT / "script.js").read_text(encoding="utf-8")

    extra_css = REVIEW_CSS + REVIEW_LOWRES_CSS
    if hero_wide:
        extra_css += "\n" + HERO_WIDE_CSS
    if hero_pdf:
        extra_css += "\n" + HERO_PDF_CSS
        a = html.find("  <!-- ============ ヒーロー① ")
        s2 = html.find('<section class="hero2">')
        e = html.find("</section>", s2)
        if a < 0 or s2 < 0 or e < 0:
            sys.exit("!! ヒーロー①②の位置が見つからない（index.html を書き換えた？）")
        html = html[:a] + HERO_PDF_HTML + html[e + len("</section>"):]
    if password:
        extra_css += "\n  " + GATE_CSS

    # CSS を <style> に埋め込む
    html, n = re.subn(r'  <link rel="stylesheet" href="style\.css[^"]*">',
                      "  <style>\n" + css + extra_css + "\n</style>", html)
    if n != 1:
        sys.exit("!! style.css の <link> が見つからない（index.html を書き換えた？）")

    # JS を <script> に埋め込む
    budoux = (ROOT / "budoux-ja.min.js").read_text(encoding="utf-8")
    html, n = re.subn(r'  <script src="budoux-ja\.min\.js"></script>',
                      lambda m: "  <script>\n" + budoux + "\n  </script>", html)
    if n != 1:
        sys.exit("!! budoux-ja.min.js の <script> が見つからない（改行の制御が効かなくなる）")
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

    note = (HERO_PDF_NOTE if hero_pdf else HERO_WIDE_NOTE if hero_wide else REVIEW_NOTE).format(date=date)

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
    ap.add_argument("--hero-wide", action="store_true",
                    help="大村さん案：スマホでもヒーローを横長にした比較版を作る")
    ap.add_argument("--hero-pdf", dest="hero_pdf", action="store_true", default=True,
                    help="ヒーローにカンプPDFをそのまま画像で貼る（＝正規版・既定）")
    ap.add_argument("--no-hero-pdf", dest="hero_pdf", action="store_false",
                    help="ヒーローを本体のまま（旧・縦長版）にする")
    args = ap.parse_args()

    # 横長版を作るときは、PDF貼り付けのヒーローは使わない
    hero_pdf = args.hero_pdf and not args.hero_wide
    html = build(None if args.no_gate else args.password, args.date, hero_wide=args.hero_wide, hero_pdf=hero_pdf)
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
              ' && git add rs-ridersin-p-8k2d && git commit -m "ライダーズ確認用を更新" && git push')


if __name__ == "__main__":
    main()
