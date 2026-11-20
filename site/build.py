#!/usr/bin/env python3
"""Build the public profile website from the LaTeX CV.

The .tex files are the single source of truth: this script reads resume.tex /
resume_vi.tex, follows their \\input{cv/...} list in order, and renders each
\\cvsection into HTML. Edit the CV, push, and GitHub Actions rebuilds the site.

    python3 site/build.py            # writes _site/ (index.html, vi/index.html)
    python3 site/build.py --out DIR

Phone and address are never read: they live in private/ (git-ignored).
"""
from __future__ import annotations

import argparse
import html
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_SRC = Path(__file__).resolve().parent

LANGS = {
    "en": {"tex": "resume.tex", "path": "", "html_lang": "en", "pdf": "VuVietAnh_CV.pdf",
           "ui": {"download": "Download CV (PDF)", "switch": "Tiếng Việt", "updated": "Last updated",
                  "built": "Generated from my LaTeX CV", "contents": "Contents", "top": "Back to top",
                  "role": "AI Engineer · Machine Learning Researcher"}},
    "vi": {"tex": "resume_vi.tex", "path": "vi/", "html_lang": "vi", "pdf": "VuVietAnh_CV_vi.pdf",
           "ui": {"download": "Tải CV (PDF)", "switch": "English", "updated": "Cập nhật lần cuối",
                  "built": "Tự động tạo từ CV LaTeX", "contents": "Mục lục", "top": "Lên đầu trang",
                  "role": "Kỹ sư AI · Nghiên cứu Học máy"}},
}


# --------------------------------------------------------------------------- #
#  Low-level LaTeX scanning
# --------------------------------------------------------------------------- #
def strip_comments(tex: str) -> str:
    """Drop % comments (but keep escaped \\%)."""
    out = []
    for line in tex.split("\n"):
        m = re.search(r"(?<!\\)%", line)
        out.append(line[: m.start()] if m else line)
    return "\n".join(out)


def read_group(s: str, i: int, open_c: str = "{", close_c: str = "}") -> tuple[str, int]:
    """s[i] must be open_c (after skipping whitespace). Return (content, index after close)."""
    while i < len(s) and s[i].isspace():
        i += 1
    if i >= len(s) or s[i] != open_c:
        raise ValueError(f"expected {open_c!r} at {i}: {s[i:i+40]!r}")
    depth, j = 0, i
    while j < len(s):
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == open_c:
            depth += 1
        elif c == close_c:
            depth -= 1
            if depth == 0:
                return s[i + 1 : j], j + 1
        j += 1
    raise ValueError(f"unbalanced group starting at {i}: {s[i:i+60]!r}")


def read_args(s: str, i: int, n: int) -> tuple[list[str], int]:
    args = []
    for _ in range(n):
        a, i = read_group(s, i)
        args.append(a)
    return args, i


def find_macro_calls(s: str, name: str, nargs: int) -> list[list[str]]:
    calls, i = [], 0
    pat = re.compile(r"\\" + name + r"(?![A-Za-z])")
    while True:
        m = pat.search(s, i)
        if not m:
            return calls
        args, i = read_args(s, m.end(), nargs)
        calls.append(args)


def env_body(s: str, env: str) -> list[str]:
    return re.findall(r"\\begin\{" + env + r"\}(.*?)\\end\{" + env + r"\}", s, flags=re.S)


def split_items(s: str) -> list[str]:
    """Split an itemize/cvitems body on top-level \\item."""
    parts, depth, last, i = [], 0, None, 0
    while i < len(s):
        c = s[i]
        if c == "\\":
            if depth == 0 and s.startswith("\\item", i) and not s[i + 5 : i + 6].isalpha():
                if last is not None:
                    parts.append(s[last:i])
                last = i + 5
                i += 5
                continue
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    if last is not None:
        parts.append(s[last:])
    items = []
    for p in parts:
        p = p.strip()
        # "\item {text}" -- unwrap a single enclosing group
        if p.startswith("{"):
            inner, end = read_group(p, 0)
            if not p[end:].strip():
                p = inner
        items.append(p.strip())
    return [p for p in items if p]


# --------------------------------------------------------------------------- #
#  Inline LaTeX -> HTML
# --------------------------------------------------------------------------- #
SIMPLE_WRAP = {
    "textbf": ("<strong>", "</strong>"), "bf": ("<strong>", "</strong>"),
    "textit": ("<em>", "</em>"), "emph": ("<em>", "</em>"), "it": ("<em>", "</em>"),
    "underline": ("", ""), "textnormal": ("", ""), "strut": ("", ""),
    "footnotesize": ("", ""), "large": ("", ""), "small": ("", ""),
}
MATH = {
    r"\sim": "~", r"\rightarrow": "→", r"\leftarrow": "←", r"\leftrightarrow": "↔",
    r"\pm": "±", r"\times": "×", r"\geq": "≥", r"\leq": "≤", r"\approx": "≈",
}
SYMBOLS = {
    r"\&": "&amp;", r"\%": "%", r"\_": "_", r"\#": "#", r"\$": "$",
    r"\,": "&#8239;", r"\ ": " ", r"\newline": "<br>", r"\\": "<br>",
}


def inline(s: str) -> str:
    s = re.sub(r"\n[ \t]*\n\s*", r" \\newline ", s.strip())  # blank line = paragraph break
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "$":
            j = s.index("$", i + 1)
            math = s[i + 1 : j].strip()
            out.append(html.escape(MATH.get(math, math.replace("\\", ""))))
            i = j + 1
            continue
        if c == "\\":
            for sym, rep in SYMBOLS.items():
                if s.startswith(sym, i) and not (sym[1:].isalpha() and s[i + len(sym) : i + len(sym) + 1].isalpha()):
                    out.append(rep)
                    i += len(sym)
                    break
            else:
                m = re.match(r"\\([A-Za-z]+)\*?", s[i:])
                if not m:
                    i += 1
                    continue
                name, i = m.group(1), i + m.end()
                if name == "href":
                    (url, text), i = read_args(s, i, 2)
                    out.append(f'<a href="{html.escape(url.strip())}">{inline(text)}</a>')
                elif name == "textcolor":
                    (color, text), i = read_args(s, i, 2)
                    cls = "hl" if color.strip() == "blue" else ""
                    out.append(f'<span class="{cls}">{inline(text)}</span>' if cls else inline(text))
                elif name in SIMPLE_WRAP:
                    a, b = SIMPLE_WRAP[name]
                    rest = s[i:].lstrip()
                    if rest.startswith("{"):
                        arg, i = read_group(s, i)
                        out.append(a + inline(arg) + b)
                    else:  # declaration form, e.g. {\bf X}
                        out.append(a + inline(s[i:]) + b)
                        i = len(s)
                elif name in ("vspace", "hspace"):
                    _, i = read_group(s, i)
                else:  # unknown macro: drop the command, keep its argument text
                    pass
            continue
        if c == "{":
            arg, i = read_group(s, i)
            out.append(inline(arg))
            continue
        if c == "}":
            i += 1
            continue
        if s.startswith("``", i):
            out.append("“"); i += 2; continue
        if s.startswith("''", i):
            out.append("”"); i += 2; continue
        if s.startswith("---", i):
            out.append("—"); i += 3; continue
        if s.startswith("--", i):
            out.append("–"); i += 2; continue
        if c == "~":
            out.append("&nbsp;"); i += 1; continue
        out.append(html.escape(c))
        i += 1
    return re.sub(r"\s+", " ", "".join(out)).strip()


def plain(s: str) -> str:
    return re.sub(r"<[^>]+>", "", inline(s)).replace("&amp;", "&")


# --------------------------------------------------------------------------- #
#  Section parsing -> HTML blocks
# --------------------------------------------------------------------------- #
PROJECT_PREFIX = re.compile(r"^(Project|Dự án)\s*:\s*", re.I)


def render_entries(body: str) -> str:
    out = []
    for title, _loc, desc in find_macro_calls(body, "cventry", 3):
        items = []
        for block in env_body(desc, "cvitems"):
            items += split_items(block)
        lis = "".join(f"<li>{inline(it)}</li>" for it in items)
        out.append(f'<article class="project"><h4>{PROJECT_PREFIX.sub("", inline(title))}</h4>'
                   + (f"<ul>{lis}</ul>" if lis else "") + "</article>")
    return "".join(out)


def split_top(s: str, sep: str = ",") -> list[str]:
    """Split on sep outside (), [] and {}."""
    parts, depth, cur = [], 0, ""
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append(cur.strip()); cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def job_header(org: str, when: str) -> str:
    """'Company, \\textnormal{\\textit{Role} | City}' -> company / role · city."""
    m = re.match(r"\s*(.*?),\s*\\textnormal\s*\{(.*)\}\s*$", org, flags=re.S)
    if m:
        company = inline(m.group(1))
        detail = " · ".join(plain(x) for x in m.group(2).split("|") if x.strip())
    else:
        company, detail = inline(org), ""
    sub = f'<p class="sub">{html.escape(detail)}</p>' if detail else ""
    return (f'<header class="block-head"><div><h3>{company}</h3>{sub}</div>'
            f'<time>{inline(when)}</time></header>')


def render_section(body: str) -> str:
    """Walk the section body in source order, emitting HTML per known block.

    A job (\\cventrynew) or research group (\\cvgroupheader) opens a block; the
    \\cventry projects that follow are nested inside it until the next one.
    """
    tokens = re.compile(
        r"\\begin\{(cvparagraph|cvhonors|cventries2|cventries|cvskills|itemize)\}"
        r"|\\cvgroupheader(?=\s*\{)"
    )
    out, i, open_block = [], 0, False

    def close():
        nonlocal open_block
        if open_block:
            out.append("</div></div>")
            open_block = False

    while True:
        m = tokens.search(body, i)
        if not m:
            break
        if m.group(0).startswith("\\cvgroupheader"):
            (name, note), i = read_args(body, m.end(), 2)
            close()
            out.append(f'<div class="block"><header class="block-head"><div><h3>{inline(name)}</h3>'
                       f'<p class="sub">{inline(note)}</p></div></header><div class="projects">')
            open_block = True
            continue
        env = m.group(1)
        end = body.index("\\end{" + env + "}", m.end())
        inner = body[m.end() : end]
        i = end + len("\\end{" + env + "}")
        if env == "cventries2":
            for org, when, _ in find_macro_calls(inner, "cventrynew", 3):
                close()
                out.append(f'<div class="block">{job_header(org, when)}<div class="projects">')
                open_block = True
            continue
        if env == "cventries":
            entries = render_entries(inner)
            out.append(entries if open_block else f'<div class="projects">{entries}</div>')
            continue
        close()
        if env == "cvparagraph":
            out.append(f'<p class="lead">{inline(inner)}</p>')
        elif env == "cvhonors":
            rows = "".join(
                f'<li class="row"><div>{inline(what)}</div><time>{inline(when)}</time></li>'
                for what, when in find_macro_calls(inner, "cvhonor", 2))
            out.append(f'<ul class="rows">{rows}</ul>')
        elif env == "cvskills":
            pairs = find_macro_calls(inner, "cvskill", 2)
            as_tags = any(len(split_top(plain(v))) > 1 for _, v in pairs)
            if as_tags:
                rows = "".join(
                    f'<div class="skill"><h4>{inline(k)}</h4><ul class="tags">'
                    + "".join(f"<li>{html.escape(t)}</li>" for t in split_top(plain(v)))
                    + "</ul></div>" for k, v in pairs)
                out.append(f'<div class="skills">{rows}</div>')
            else:
                rows = "".join(f"<dt>{inline(k)}</dt><dd>{inline(v)}</dd>" for k, v in pairs)
                out.append(f'<dl class="kv">{rows}</dl>')
        elif env == "itemize":
            lis = "".join(f"<li>{inline(it)}</li>" for it in split_items(inner))
            out.append(f'<ul class="bullets">{lis}</ul>')
    close()
    return "\n".join(out)


def parse_sections(tex_file: Path) -> list[tuple[str, str]]:
    main = strip_comments(tex_file.read_text(encoding="utf-8"))
    doc = main.split("\\begin{document}", 1)[1]
    sections = []
    for inc in re.findall(r"\\input\{([^}]+)\}", doc):
        src = strip_comments((ROOT / (inc if inc.endswith(".tex") else inc + ".tex")).read_text(encoding="utf-8"))
        # a file may hold several \cvsection blocks (e.g. publications + certifications)
        heads = list(re.finditer(r"\\cvsection\{", src))
        for k, h in enumerate(heads):
            title, start = read_group(src, h.end() - 1)
            stop = heads[k + 1].start() if k + 1 < len(heads) else len(src)
            sections.append((plain(title), render_section(src[start:stop])))
    return sections


def parse_header(tex_file: Path) -> dict:
    s = strip_comments(tex_file.read_text(encoding="utf-8"))
    first, last = find_macro_calls(s, "name", 2)[0]
    info = {"name": f"{plain(first)} {plain(last)}".strip()}
    for key in ("email", "github"):
        calls = find_macro_calls(s, key, 1)
        info[key] = calls[0][0].strip() if calls else None
    quote = find_macro_calls(s, "quote", 1)
    info["links"] = re.findall(r"\\href\{([^}]+)\}", quote[0][0]) if quote else []
    return info


# --------------------------------------------------------------------------- #
#  Page assembly
# --------------------------------------------------------------------------- #
ICONS = {
    "email": '<path d="M3 5h18v14H3z" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="m3 6 9 7 9-7" fill="none" stroke="currentColor" stroke-width="1.8"/>',
    "github": '<path fill="currentColor" d="M12 2a10 10 0 0 0-3.2 19.5c.5.1.7-.2.7-.5v-1.7c-2.8.6-3.4-1.3-3.4-1.3-.5-1.2-1.1-1.5-1.1-1.5-.9-.6.1-.6.1-.6 1 .1 1.5 1 1.5 1 .9 1.5 2.3 1.1 2.9.8.1-.6.3-1.1.6-1.3-2.2-.3-4.6-1.1-4.6-5 0-1.1.4-2 1-2.7-.1-.2-.4-1.3.1-2.7 0 0 .8-.3 2.8 1a9.6 9.6 0 0 1 5 0c1.9-1.3 2.8-1 2.8-1 .5 1.4.2 2.4.1 2.7.6.7 1 1.6 1 2.7 0 3.9-2.4 4.7-4.6 5 .4.3.7.9.7 1.9V21c0 .3.2.6.7.5A10 10 0 0 0 12 2Z"/>',
    "linkedin": '<path fill="currentColor" d="M4.98 3.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5ZM3 9.5h4V21H3zM9.5 9.5h3.8v1.6h.1c.5-1 1.8-2 3.8-2 4 0 4.8 2.6 4.8 6V21h-4v-5.2c0-1.2 0-2.9-1.8-2.9s-2 1.4-2 2.8V21h-4z"/>',
    "orcid": '<circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="1.8"/><path fill="currentColor" d="M8 7.2a1 1 0 1 1 0 2 1 1 0 0 1 0-2Zm-.8 3h1.6v7h-1.6zm3 0h3c2.6 0 3.9 1.7 3.9 3.5 0 2-1.5 3.5-3.9 3.5h-3zm1.6 1.4v4.2h1.3c1.7 0 2.4-1 2.4-2.1 0-1.2-.8-2.1-2.4-2.1z"/>',
}


def icon(name: str) -> str:
    return f'<svg viewBox="0 0 24 24" aria-hidden="true">{ICONS[name]}</svg>'


def contact_links(h: dict) -> str:
    links = []
    if h["email"]:
        links.append(f'<a href="mailto:{html.escape(h["email"])}">{icon("email")}<span>{html.escape(h["email"])}</span></a>')
    if h["github"]:
        url = h["github"] if h["github"].startswith("http") else "https://" + h["github"]
        links.append(f'<a href="{html.escape(url)}">{icon("github")}<span>{html.escape(h["github"])}</span></a>')
    for url in h["links"]:
        kind = "linkedin" if "linkedin" in url else "orcid" if "orcid" in url else None
        if kind:
            label = re.sub(r"^https?://(www\.)?", "", url).rstrip("/")
            links.append(f'<a href="{html.escape(url)}">{icon(kind)}<span>{html.escape(label)}</span></a>')
    return "".join(links)


def slug(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-") or "section"


def build_page(lang: str, other: str, template: str, has_pdf: bool) -> str:
    cfg, ocfg = LANGS[lang], LANGS[other]
    ui = cfg["ui"]
    head = parse_header(ROOT / cfg["tex"])
    sections = parse_sections(ROOT / cfg["tex"])
    up = "../" if cfg["path"] else ""
    lead = next((k for k, (_, c) in enumerate(sections) if c.startswith('<p class="lead">')), None)
    summary_html = ""
    if lead is not None:
        summary_html = re.sub(r'^<p class="lead">|</p>$', "", sections.pop(lead)[1])
    nav = "".join(f'<a href="#{slug(t)}">{html.escape(t.title())}</a>' for t, _ in sections)
    body = "\n".join(
        f'<section id="{slug(t)}"><h2>{html.escape(t.title())}</h2><div class="content">{content}</div></section>'
        for t, content in sections)
    pdf_btn = (f'<a class="btn" href="{up}{cfg["pdf"]}" download>{ui["download"]}</a>' if has_pdf else "")
    summary = re.sub(r"<[^>]+>", "", summary_html)
    replacements = {
        "LANG": cfg["html_lang"], "NAME": html.escape(head["name"].title()),
        "DESCRIPTION": html.escape(summary[:200]), "UP": up, "SUMMARY": summary_html,
        "ROLE": ui["role"],
        "CONTACT": contact_links(head), "BODY": body, "PDF_BUTTON": pdf_btn,
        "SWITCH_HREF": up + ocfg["path"], "SWITCH_LABEL": ui["switch"],
        "CONTENTS": ui["contents"],
    }
    page = template
    for k, v in replacements.items():
        page = page.replace("{{" + k + "}}", v)
    leftover = re.findall(r"\{\{[A-Z_]+\}\}", page)
    if leftover:
        raise SystemExit(f"unfilled template slots: {leftover}")
    return page


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "_site"))
    args = ap.parse_args()
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    template = (SITE_SRC / "template.html").read_text(encoding="utf-8")
    pdfs = {"en": ROOT / "resume.pdf", "vi": ROOT / "resume_vi.pdf"}
    has_pdf = all(p.exists() for p in pdfs.values())
    for lang, other in (("en", "vi"), ("vi", "en")):
        target = out / LANGS[lang]["path"] / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(build_page(lang, other, template, has_pdf), encoding="utf-8")
        if has_pdf:
            shutil.copy(pdfs[lang], out / LANGS[lang]["pdf"])
    shutil.copy(SITE_SRC / "style.css", out / "style.css")
    shutil.copy(ROOT / "avatar.png", out / "avatar.png")
    (out / ".nojekyll").write_text("")
    print(f"site written to {out} (PDF download: {'yes' if has_pdf else 'no'})")


if __name__ == "__main__":
    sys.exit(main())
