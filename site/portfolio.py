"""Portfolio homepage and blog for the profile site.

The homepage (/, /vi/) is rendered from site/content.json; blog posts from site/posts/*.md.
The CV pages (/cv/, /vi/cv/) are still generated from the .tex files by build.py.
Stdlib only, so the GitHub Actions build needs no extra packages.
"""
from __future__ import annotations

import html
import json
import re
from datetime import date
from pathlib import Path

SITE_SRC = Path(__file__).resolve().parent

UI = {
    "en": {"nav": [("about", "About"), ("news", "News"), ("publications", "Publications"), ("research", "Research"),
                   ("open-source", "Open source"), ("experience", "Experience"), ("writing", "Writing")],
           "cv": "CV", "switch": "Tiếng Việt", "news": "News", "pubs": "Publications", "research": "Research",
           "oss": "Open source", "exp": "Experience", "awards": "Awards", "edu": "Education", "writing": "Writing",
           "fullcv": "Full CV", "short": "2-page versions", "acad": "academic", "ind": "industry", "pdf": "CV (PDF)", "bibtex": "BibTeX", "copy": "Copy", "copied": "Copied",
           "also": "More repositories", "read": "Read", "back": "All writing", "updated": "Updated",
           "built": "Built with Python from my LaTeX CV",
           "post_lang": "", "interests": "Research interests", "home": "Home"},
    "vi": {"nav": [("about", "Giới thiệu"), ("news", "Tin mới"), ("publications", "Công bố"), ("research", "Nghiên cứu"),
                   ("open-source", "Mã nguồn mở"), ("experience", "Kinh nghiệm"), ("writing", "Bài viết")],
           "cv": "CV", "switch": "English", "news": "Tin mới", "pubs": "Công bố khoa học", "research": "Hướng nghiên cứu",
           "oss": "Mã nguồn mở", "exp": "Kinh nghiệm", "awards": "Giải thưởng", "edu": "Học vấn", "writing": "Bài viết",
           "fullcv": "CV đầy đủ", "short": "Bản rút gọn 2 trang", "acad": "học thuật", "ind": "công nghiệp", "pdf": "CV (PDF)", "bibtex": "BibTeX", "copy": "Sao chép", "copied": "Đã chép",
           "also": "Repo khác", "read": "Đọc", "back": "Tất cả bài viết", "updated": "Cập nhật",
           "built": "Tự động tạo bằng Python từ CV LaTeX",
           "post_lang": " (English)", "interests": "Quan tâm nghiên cứu", "home": "Trang chủ"},
}
PDF = {"en": "VuVietAnh_CV.pdf", "vi": "VuVietAnh_CV_vi.pdf"}
MONTHS = {"en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
          "vi": [f"Th{m}" for m in range(1, 13)]}

ICONS = {
    "email": '<path d="M3 5h18v14H3z" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="m3 6 9 7 9-7" fill="none" stroke="currentColor" stroke-width="1.8"/>',
    "github": '<path fill="currentColor" d="M12 2a10 10 0 0 0-3.2 19.5c.5.1.7-.2.7-.5v-1.7c-2.8.6-3.4-1.3-3.4-1.3-.5-1.2-1.1-1.5-1.1-1.5-.9-.6.1-.6.1-.6 1 .1 1.5 1 1.5 1 .9 1.5 2.3 1.1 2.9.8.1-.6.3-1.1.6-1.3-2.2-.3-4.6-1.1-4.6-5 0-1.1.4-2 1-2.7-.1-.2-.4-1.3.1-2.7 0 0 .8-.3 2.8 1a9.6 9.6 0 0 1 5 0c1.9-1.3 2.8-1 2.8-1 .5 1.4.2 2.4.1 2.7.6.7 1 1.6 1 2.7 0 3.9-2.4 4.7-4.6 5 .4.3.7.9.7 1.9V21c0 .3.2.6.7.5A10 10 0 0 0 12 2Z"/>',
    "linkedin": '<path fill="currentColor" d="M4.98 3.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5ZM3 9.5h4V21H3zM9.5 9.5h3.8v1.6h.1c.5-1 1.8-2 3.8-2 4 0 4.8 2.6 4.8 6V21h-4v-5.2c0-1.2 0-2.9-1.8-2.9s-2 1.4-2 2.8V21h-4z"/>',
    "orcid": '<circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="1.8"/><path fill="currentColor" d="M8 7.2a1 1 0 1 1 0 2 1 1 0 0 1 0-2Zm-.8 3h1.6v7h-1.6zm3 0h3c2.6 0 3.9 1.7 3.9 3.5 0 2-1.5 3.5-3.9 3.5h-3zm1.6 1.4v4.2h1.3c1.7 0 2.4-1 2.4-2.1 0-1.2-.8-2.1-2.4-2.1z"/>',
    "scholar": '<path fill="currentColor" d="M12 3 1 9l11 6 9-4.9V17h2V9L12 3Zm-6 9.5V16c0 1.7 2.7 3 6 3s6-1.3 6-3v-3.5l-6 3.3-6-3.3Z"/>',
    "pdf": '<path d="M7 3h7l5 5v13H7z" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M14 3v5h5" fill="none" stroke="currentColor" stroke-width="1.8"/>',
    "arrow": '<path d="M5 12h14m-6-6 6 6-6 6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
}

# Schematic for the VISTA paper (no figure is published with the paper). Uses CSS variables so it follows the theme.
VISTA_SVG = """<svg viewBox="0 0 600 220" role="img" aria-label="VISTA: variable-length GA with an LSTM surrogate selecting classifiers in a multi-layer ensemble" style="font-family:var(--sans)">
<defs><marker id="va" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10z" fill="var(--muted)"/></marker></defs>
<g font-size="13" text-anchor="middle">
<rect x="14" y="58" width="150" height="88" rx="10" fill="var(--bg-soft)" stroke="var(--line-strong)"/>
<text x="89" y="88" font-weight="600" fill="var(--text)">Variable-length</text><text x="89" y="106" font-weight="600" fill="var(--text)">chromosomes</text>
<text x="89" y="128" font-size="11.5" fill="var(--muted)">candidate ensembles</text>
<rect x="224" y="58" width="150" height="88" rx="10" fill="var(--accent-soft)" stroke="var(--accent-2)"/>
<text x="299" y="88" font-weight="600" fill="var(--text)">LSTM surrogate</text>
<text x="299" y="108" font-size="11.5" fill="var(--muted)">variable → fixed length</text><text x="299" y="126" font-size="11.5" fill="var(--muted)">predicts fitness</text>
<rect x="434" y="58" width="150" height="88" rx="10" fill="var(--bg-soft)" stroke="var(--line-strong)"/>
<text x="509" y="88" font-weight="600" fill="var(--text)">Multi-layer</text><text x="509" y="106" font-weight="600" fill="var(--text)">ensemble</text>
<text x="509" y="128" font-size="11.5" fill="var(--muted)">best subset per layer</text>
<path d="M164 102h56" stroke="var(--muted)" stroke-width="1.6" marker-end="url(#va)"/>
<path d="M374 102h56" stroke="var(--muted)" stroke-width="1.6" marker-end="url(#va)"/>
<path d="M299 146v34H89v-30" fill="none" stroke="var(--accent-2)" stroke-width="1.6" stroke-dasharray="5 4" marker-end="url(#va)"/>
<text x="194" y="200" font-size="11.5" fill="var(--accent-2)">selection · crossover · mutation</text>
<text x="300" y="34" font-size="12" fill="var(--muted)">surrogate-assisted ensemble selection (VISTA)</text>
</g></svg>"""


def t(v, lang):
    """A content field: {"en":..., "vi":...} or a plain value used for both languages."""
    return v.get(lang, v.get("en")) if isinstance(v, dict) else v


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def icon(name: str) -> str:
    return f'<svg class="i" viewBox="0 0 24 24" aria-hidden="true">{ICONS[name]}</svg>'


def picture(fig: dict, up: str, cls: str = "") -> str:
    if fig.get("inline") == "vista":
        return f'<div class="fig {cls}">{VISTA_SVG}</div>'
    return (f'<picture class="fig {cls}"><source media="(prefers-color-scheme: dark)" srcset="{up}{fig["dark"]}">'
            f'<img src="{up}{fig["light"]}" alt="{esc(fig["alt"])}" loading="lazy"></picture>')


def fmt_date(d: str, lang: str) -> str:
    parts = d.split("-")
    if len(parts) >= 2:
        return f'{MONTHS[lang][int(parts[1]) - 1]} {parts[0]}'
    return parts[0]


# --------------------------------------------------------------------------- #
#  Minimal Markdown (headings, paragraphs, lists, tables, fenced code, inline)
# --------------------------------------------------------------------------- #
def md_inline(s: str) -> str:
    codes: list[str] = []

    def keep(m):
        codes.append(f"<code>{esc(m.group(1))}</code>")
        return f"\x00{len(codes) - 1}\x00"

    s = re.sub(r"`([^`]+)`", keep, s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', s)
    return re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], s)


def markdown(src: str) -> str:
    out, lines, i = [], src.split("\n"), 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("```"):
            lang = line[3:].strip()
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            code = esc("\n".join(lines[i + 1:j]))
            out.append(f'<pre><code class="lang-{esc(lang)}">{code}</code></pre>')
            i = j + 1
            continue
        m = re.match(r"(#{2,4})\s+(.*)", line)
        if m:
            lvl = len(m.group(1))
            text = md_inline(m.group(2))
            out.append(f'<h{lvl} id="{re.sub(r"[^a-z0-9]+", "-", re.sub(r"<[^>]+>", "", text).lower()).strip("-")}">{text}</h{lvl}>')
            i += 1
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head, body = rows[0], [r for r in rows[1:] if not all(re.fullmatch(r":?-+:?", c) for c in r)]
            th = "".join(f"<th>{md_inline(c)}</th>" for c in head)
            trs = "".join("<tr>" + "".join(f"<td>{md_inline(c)}</td>" for c in r) + "</tr>" for r in body)
            out.append(f'<div class="table"><table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>')
            continue
        if re.match(r"[-*]\s+", line):
            items = []
            while i < len(lines) and (re.match(r"[-*]\s+", lines[i]) or (lines[i].startswith("  ") and items)):
                if re.match(r"[-*]\s+", lines[i]):
                    items.append(re.sub(r"^[-*]\s+", "", lines[i]))
                else:
                    items[-1] += " " + lines[i].strip()
                i += 1
            out.append("<ul>" + "".join(f"<li>{md_inline(x)}</li>" for x in items) + "</ul>")
            continue
        para = []
        while i < len(lines) and lines[i].strip() and not re.match(r"(```|#{2,4}\s|\||[-*]\s)", lines[i]):
            para.append(lines[i].strip())
            i += 1
        out.append(f"<p>{md_inline(' '.join(para))}</p>")
    return "\n".join(out)


def load_posts() -> list[dict]:
    posts = []
    for p in sorted((SITE_SRC / "posts").glob("*.md")):
        raw = p.read_text(encoding="utf-8")
        m = re.match(r"---\n(.*?)\n---\n(.*)", raw, flags=re.S)
        meta = dict(re.findall(r"^(\w+):\s*(.*)$", m.group(1), flags=re.M)) if m else {}
        body = m.group(2) if m else raw
        posts.append({"slug": p.stem, "title": meta.get("title", p.stem), "date": meta.get("date", ""),
                      "summary": meta.get("summary", ""), "html": markdown(body),
                      "minutes": max(1, round(len(re.findall(r"\w+", body)) / 220))})
    return sorted(posts, key=lambda x: x["date"], reverse=True)


# --------------------------------------------------------------------------- #
#  Page shell
# --------------------------------------------------------------------------- #
def shell(*, lang: str, title: str, description: str, up: str, body: str, nav: str, switch_href: str,
          canonical_path: str, og_image: str = "avatar.png") -> str:
    ui = UI[lang]
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:type" content="website">
<meta property="og:url" content="https://vuvietanh2309.github.io/{canonical_path}">
<meta property="og:image" content="https://vuvietanh2309.github.io/{og_image}">
<link rel="canonical" href="https://vuvietanh2309.github.io/{canonical_path}">
<link rel="icon" href="{up}avatar.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Newsreader:opsz,wght@6..72,500;6..72,600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{up}style.css">
</head>
<body id="top" class="portfolio">
<header class="bar">
  <div class="bar-inner">
    <a class="brand" href="{up}{'vi/' if lang == 'vi' else ''}">Viet Anh Vu</a>
    <nav class="links">{nav}</nav>
    <div class="bar-actions">
      <a class="lang" href="{switch_href}">{ui['switch']}</a>
      <a class="btn" href="{up}{'vi/' if lang == 'vi' else ''}cv/">{ui['cv']}</a>
    </div>
  </div>
</header>
{body}
<footer class="foot">
  <div class="wrap foot-inner">
    <span>© {date.today().year} Viet Anh Vu · {ui['updated']} {date.today().strftime('%d %b %Y')}</span>
    <span class="muted">{ui['built']}</span>
  </div>
</footer>
<script>
document.querySelectorAll('[data-toggle]').forEach(b => b.addEventListener('click', () => {{
  const box = document.getElementById(b.dataset.toggle); box.hidden = !box.hidden;
  b.setAttribute('aria-expanded', String(!box.hidden));
}}));
document.querySelectorAll('[data-copy]').forEach(b => b.addEventListener('click', () => {{
  const pre = document.getElementById(b.dataset.copy);
  navigator.clipboard.writeText(pre.innerText).then(() => {{
    const old = b.textContent; b.textContent = b.dataset.done; setTimeout(() => b.textContent = old, 1500);
  }}).catch(() => {{}});
}}));
</script>
</body>
</html>
"""


# --------------------------------------------------------------------------- #
#  Homepage
# --------------------------------------------------------------------------- #
def links_row(c: dict, lang: str, up: str) -> str:
    items = []
    for l in c["links"]:
        if not l["url"]:
            continue
        label = esc(l["label"])
        items.append(f'<a class="chip" href="{esc(l["url"])}">{icon(l["kind"])}<span>{label}</span></a>')
    items.append(f'<a class="chip chip-strong" href="{up}{PDF[lang]}">{icon("pdf")}<span>{UI[lang]["pdf"]}</span></a>')
    ui = UI[lang]
    items.append(f'<span class="short-cv">{ui["short"]}: <a href="{up}VuVietAnh_CV_2p_academic.pdf">{ui["acad"]}</a>'
                 f' · <a href="{up}VuVietAnh_CV_2p_industry.pdf">{ui["ind"]}</a></span>')
    return "".join(items)


def build_home(c: dict, lang: str, posts: list[dict]) -> str:
    ui = UI[lang]
    up = "../" if lang == "vi" else ""
    sec = lambda id_, title, inner, extra="": (
        f'<section id="{id_}" class="sec {extra}"><div class="wrap"><h2>{title}</h2>{inner}</div></section>')

    hero = f"""
<section id="about" class="intro"><div class="wrap intro-inner">
  <div class="intro-text">
    <p class="eyebrow">{esc(t(c['role'], lang))}</p>
    <h1>{esc(c['name'])} <span class="native">{esc(c['name_native'])}</span></h1>
    <p class="aff">{esc(t(c['affiliation'], lang))}</p>
    <p class="bio">{t(c['bio'], lang)}</p>
    <ul class="interests" aria-label="{ui['interests']}">{''.join(f'<li>{esc(x)}</li>' for x in t(c['interests'], lang))}</ul>
    <nav class="chips">{links_row(c, lang, up)}</nav>
  </div>
  <img class="portrait" src="{up}avatar.png" alt="{esc(c['name'])}" width="280" height="350">
</div></section>"""

    news = "".join(f'<li><time>{fmt_date(n["date"], lang)}</time><span>{t(n["text"], lang)}</span></li>'
                   for n in c["news"])

    pubs = []
    for k, p in enumerate(c["publications"]):
        btns = "".join(f'<a class="pill" href="{esc(l["url"])}">{esc(l["label"])}</a>' for l in p["links"])
        pubs.append(f"""
<article class="pub">
  {picture(p['figure'], up, 'pub-fig')}
  <div class="pub-body">
    <p class="venue">{esc(p['venue_short'])}</p>
    <h3>{esc(p['title'])}</h3>
    <p class="authors">{p['authors']}</p>
    <p class="venue-full">{esc(p['venue'])}</p>
    <p class="pub-sum">{esc(t(p['summary'], lang))}</p>
    <div class="pub-actions">{btns}
      <button class="pill" type="button" aria-expanded="false" aria-controls="bibbox{k}" data-toggle="bibbox{k}">{ui['bibtex']}</button>
      <div class="bib-box" id="bibbox{k}" hidden><button class="copy" type="button" data-copy="bib{k}" data-done="{ui['copied']}">{ui['copy']}</button><pre id="bib{k}">{esc(p['bibtex'])}</pre></div>
    </div>
  </div>
</article>""")

    research = "".join(f"""
<article class="card">
  <h3>{esc(t(r['title'], lang))}</h3>
  <p class="with">{esc(t(r['with'], lang))}</p>
  <p>{esc(t(r['text'], lang))}</p>
  <p class="card-links">{' · '.join(f'<a href="{esc(l["url"])}">{esc(l["label"])}</a>' for l in r['links'])}</p>
</article>""" for r in c["research"])

    o = c["opensource"]
    badges = "".join(f'<a href="{esc(b["url"])}"><img src="{esc(b["img"])}" alt="{esc(b["alt"])}" height="20" loading="lazy"></a>'
                     for b in o["badges"])
    others = "".join(f'<li><a href="{esc(x["url"])}">{esc(x["name"])}</a><span>{esc(t(x["text"], lang))}</span></li>'
                     for x in o["others"])
    oss = f"""
<article class="feature">
  <div class="feature-text">
    <h3><a href="{esc(o['url'])}">{esc(o['name'])}</a></h3>
    <p class="tagline">{esc(t(o['tagline'], lang))}</p>
    <div class="badges">{badges}</div>
    <ul class="ticks">{''.join(f'<li>{x}</li>' for x in t(o['points'], lang))}</ul>
    <pre class="install"><code><span class="prompt">$</span> {esc(o['install'])}</code></pre>
  </div>
  {picture(o['figure'], up, 'feature-fig')}
</article>
<h3 class="minor">{ui['also']}</h3>
<ul class="repo-list">{others}</ul>"""

    exp = "".join(f"""
<li><div class="tl-head"><h3>{esc(e['org'])}</h3><time>{esc(t(e['when'], lang))}</time></div>
<p class="tl-role">{esc(t(e['role'], lang))}</p><p>{esc(t(e['text'], lang))}</p></li>""" for e in c["experience"])
    awards = "".join(f'<li><div><strong>{esc(t(a["title"], lang))}</strong><span>{esc(t(a["detail"], lang))}</span></div><time>{esc(a["year"])}</time></li>'
                     for a in c["awards"])
    edu = "".join(f'<li><div><strong>{esc(t(e["degree"], lang))}</strong><span>{esc(t(e["school"], lang))} · {esc(e["note"])}</span></div><time>{esc(e["when"])}</time></li>'
                  for e in c["education"])

    writing = "".join(f"""
<a class="post-card" href="{up}blog/{p['slug']}/">
  <time>{esc(p['date'])} · {p['minutes']} min{ui['post_lang']}</time>
  <h3>{esc(p['title'])}</h3><p>{esc(p['summary'])}</p>
  <span class="more">{ui['read']} {icon('arrow')}</span>
</a>""" for p in posts)

    body = f"""<main>
{hero}
{sec('news', ui['news'], f'<ul class="news">{news}</ul>')}
{sec('publications', ui['pubs'], ''.join(pubs))}
{sec('research', ui['research'], f'<div class="cards">{research}</div>')}
{sec('open-source', ui['oss'], oss)}
{sec('experience', ui['exp'], f'<ol class="timeline">{exp}</ol><p class="to-cv"><a href="{up}{"vi/" if lang == "vi" else ""}cv/">{ui["fullcv"]} {icon("arrow")}</a></p>'
     + f'<div class="two"><div><h3 class="minor">{ui["awards"]}</h3><ul class="rows2">{awards}</ul></div>'
     + f'<div><h3 class="minor">{ui["edu"]}</h3><ul class="rows2">{edu}</ul></div></div>')}
{sec('writing', ui['writing'], f'<div class="posts">{writing}</div>')}
</main>"""
    nav = "".join(f'<a href="#{a}">{esc(b)}</a>' for a, b in ui["nav"])
    plain_bio = re.sub(r"<[^>]+>", "", t(c["bio"], lang))
    return shell(lang=lang, title=f"{c['name']} — {t(c['role'], lang)}", description=plain_bio[:200], up=up,
                 body=body, nav=nav, switch_href=("../" if lang == "vi" else "vi/"),
                 canonical_path=("vi/" if lang == "vi" else ""))


def build_post(p: dict) -> str:
    up = "../../"
    ui = UI["en"]
    body = f"""<main class="post wrap-narrow">
<p class="crumb"><a href="{up}#writing">← {ui['back']}</a></p>
<article>
  <header><time>{esc(p['date'])} · {p['minutes']} min read</time><h1>{esc(p['title'])}</h1>
  <p class="dek">{esc(p['summary'])}</p></header>
  <div class="prose">{p['html']}</div>
</article>
<p class="crumb end"><a href="{up}">← {ui['home']}</a></p>
</main>"""
    return shell(lang="en", title=f"{p['title']} — Viet Anh Vu", description=p["summary"], up=up, body=body,
                 nav=f'<a href="{up}#writing">{ui["writing"]}</a>', switch_href=f"{up}vi/",
                 canonical_path=f"blog/{p['slug']}/")


def build_portfolio(out: Path) -> None:
    content = json.loads((SITE_SRC / "content.json").read_text(encoding="utf-8"))
    posts = load_posts()
    for lang, path in (("en", out), ("vi", out / "vi")):
        path.mkdir(parents=True, exist_ok=True)
        (path / "index.html").write_text(build_home(content, lang, posts), encoding="utf-8")
    for p in posts:
        d = out / "blog" / p["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(build_post(p), encoding="utf-8")
