#!/usr/bin/env python3
"""Build the muse-print docs site: docs/*.md -> docs/*.html (static, no deps).

Run: python docs/build.py
Output: index.html, quickstart.html, the-journey.html, drivers.html,
        esc-e.html, camera.html, api.html  (all in docs/)
Images in docs/images/ are referenced relatively and work as-is.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

DOCS = Path(__file__).parent

PAGES = [
    ("index", "Home"),
    ("quickstart", "Quickstart"),
    ("the-journey", "The Journey"),
    ("drivers", "Drivers"),
    ("esc-e", "ESC E"),
    ("camera", "Camera Loop"),
    ("api", "API"),
]

CSS = """
:root{--bg:#0d1117;--fg:#e6edf3;--muted:#8b949e;--accent:#f0a500;
--card:#161b22;--border:#30363d;--code:#1c2128}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--fg);
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
line-height:1.65}
header{padding:52px 20px 36px;text-align:center;border-bottom:1px solid var(--border)}
header h1{font-size:2.6em;letter-spacing:1px}
header h1 .dot{color:var(--accent)}
header p{color:var(--muted);max-width:640px;margin:10px auto 0;font-size:1.1em}
nav{position:sticky;top:0;background:rgba(13,17,23,.96);
border-bottom:1px solid var(--border);padding:10px 16px;text-align:center;z-index:10}
nav a{color:var(--muted);text-decoration:none;margin:0 12px;font-size:.93em}
nav a:hover,nav a.active{color:var(--accent)}
nav a.active{font-weight:600}
main{max-width:860px;margin:0 auto;padding:40px 22px 60px}
main h1{font-size:2em;margin-bottom:18px}
main h2{font-size:1.45em;margin:34px 0 12px;
border-bottom:2px solid var(--accent);display:inline-block;padding-bottom:4px}
main h3{font-size:1.15em;margin:24px 0 8px;color:var(--accent)}
main p{margin:12px 0}
main ul,main ol{margin:12px 0 12px 28px}
main li{margin:5px 0}
main blockquote{border-left:4px solid var(--accent);background:var(--card);
padding:14px 18px;margin:18px 0;border-radius:0 8px 8px 0;color:var(--fg)}
main blockquote p{margin:6px 0}
code{background:var(--code);padding:2px 6px;border-radius:4px;font-size:.88em;
font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
pre{background:var(--code);border:1px solid var(--border);border-radius:8px;
padding:16px;overflow-x:auto;margin:16px 0}
pre code{background:none;padding:0;font-size:.85em}
main a{color:var(--accent)}
main img{max-width:100%;border:1px solid var(--border);border-radius:10px;
margin:18px 0 6px;display:block}
main em.caption,figcaption{color:var(--muted);font-size:.9em;display:block;
margin:0 0 18px}
table{border-collapse:collapse;margin:16px 0;width:100%;font-size:.93em}
th,td{border:1px solid var(--border);padding:8px 12px;text-align:left}
th{background:var(--card)}
dl{margin:14px 0}
dt{font-weight:600;margin-top:10px}
dt code{font-size:.85em}
dd{margin:2px 0 8px 18px;color:var(--fg)}
hr{border:none;border-top:1px solid var(--border);margin:30px 0}
footer{text-align:center;padding:36px 20px;color:var(--muted);
border-top:1px solid var(--border);font-size:.88em}
.kicker{color:var(--accent);font-style:italic;margin-bottom:20px;display:block}
"""

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — muse-print</title>
<style>{css}</style>
</head>
<body>
<header>
<h1>muse<span class="dot">-</span>print</h1>
<p>Drift-free Dymo label printing from a Raspberry Pi.</p>
</header>
<nav>{nav}</nav>
<main>
{body}
</main>
<footer>
muse-print &middot; <a href="https://github.com/marcocaggioni/muse-print">GitHub</a>
&middot; MIT
</footer>
</body>
</html>
"""


def esc(text: str) -> str:
    return html.escape(text)


def inline(text: str) -> str:
    """Inline markdown: images, links, code, bold, italic."""
    text = esc(text)
    # images — keep local docs/images/ paths relative
    text = re.sub(
        r'!\[([^\]]*)\]\(([^)]+)\)',
        lambda m: f'<img src="{m.group(2)}" alt="{m.group(1)}">',
        text,
    )
    # links (leave .md links pointing at sibling .html pages)
    def linkfix(m: re.Match) -> str:
        label, url = m.group(1), m.group(2)
        # Only rewrite relative .md links to sibling .html pages.
        if url.endswith(".md") and not re.match(r"^(https?://|/)", url):
            url = url[:-3] + ".html"
            if url.startswith("../"):
                url = url[3:]
        return f'<a href="{url}">{label}</a>'

    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', linkfix, text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', text)
    return text


def convert(md: str) -> tuple[str, str]:
    """Convert markdown to (title, html_body)."""
    lines = md.split("\n")
    out: list[str] = []
    i = 0
    title = "muse-print"
    in_code = False
    code_lang = ""
    code_buf: list[str] = []
    para: list[str] = []

    def flush_para():
        nonlocal para
        if not para:
            return
        # definition list: "**Term**" line followed by ": def" lines
        if para[0].startswith("**") and any(
            p.startswith(": ") for p in para[1:]
        ):
            term = inline(para[0])
            defs = "".join(
                f"<dd>{inline(p[2:])}</dd>" for p in para[1:] if p.startswith(": ")
            )
            out.append(f"<dl><dt>{term}</dt>{defs}</dl>")
        else:
            # italic caption lines right after an image paragraph
            text = "<br>".join(inline(p) for p in para)
            out.append(f"<p>{text}</p>")
        para = []

    def flush_code():
        nonlocal code_buf
        if code_buf or in_code:
            out.append(
                "<pre><code>" + esc("\n".join(code_buf)) + "</code></pre>"
            )
        code_buf = []

    while i < len(lines):
        line = lines[i]
        if in_code:
            if line.strip().startswith("```"):
                in_code = False
                flush_code()
            else:
                code_buf.append(line)
            i += 1
            continue
        stripped = line.strip()
        if stripped.startswith("```"):
            flush_para()
            in_code = True
            code_lang = stripped[3:].strip()
            i += 1
            continue
        if not stripped:
            flush_para()
            i += 1
            continue
        if stripped.startswith("# "):
            flush_para()
            title = stripped[2:].strip()
            out.append(f"<h1>{inline(title)}</h1>")
        elif stripped.startswith("## "):
            flush_para()
            out.append(f"<h2>{inline(stripped[3:].strip())}</h2>")
        elif stripped.startswith("### "):
            flush_para()
            out.append(f"<h3>{inline(stripped[4:].strip())}</h3>")
        elif stripped == "---":
            flush_para()
            out.append("<hr>")
        elif stripped.startswith("> "):
            flush_para()
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            out.append(
                "<blockquote><p>"
                + "</p><p>".join(inline(q) for q in quote)
                + "</p></blockquote>"
            )
            continue
        elif re.match(r"^(\d+[.)]|[-*])\s", stripped):
            flush_para()
            ordered = bool(re.match(r"^\d+[.)]\s", stripped))
            items = []
            while i < len(lines) and re.match(
                r"^(\d+[.)]|[-*])\s", lines[i].strip()
            ):
                items.append(
                    re.sub(r"^(\d+[.)]|[-*])\s", "", lines[i].strip())
                )
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(
                f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>"
            )
            continue
        elif stripped.startswith("|") and stripped.endswith("|"):
            flush_para()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(
                    [c.strip() for c in lines[i].strip().strip("|").split("|")]
                )
                i += 1
            # drop the separator row (---|---)
            rows = [r for r in rows if not all(re.match(r"^:?-+:?$", c) for c in r)]
            head, body = rows[0], rows[1:]
            out.append(
                "<table><thead><tr>"
                + "".join(f"<th>{inline(c)}</th>" for c in head)
                + "</tr></thead><tbody>"
                + "".join(
                    "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>"
                    for r in body
                )
                + "</tbody></table>"
            )
            continue
        else:
            # '*caption*' line directly after an image becomes figcaption
            if (
                out
                and out[-1].startswith("<p><img")
                and re.match(r"^\*.*\*$", stripped)
            ):
                out[-1] = out[-1].replace("<p>", "<figure>").replace(
                    "</p>", "</figure>"
                )
                out.append(f"<figcaption>{inline(stripped.strip('*'))}</figcaption>")
            else:
                para.append(line.strip())
        i += 1
    flush_para()
    if in_code:
        flush_code()
    return title, "\n".join(out)


def build() -> None:
    nav = "".join(
        f'<a href="{slug}.html" data-page="{slug}">{label}</a>'
        for slug, label in PAGES
    )
    for slug, label in PAGES:
        md_path = DOCS / f"{slug}.md"
        if not md_path.exists():
            print(f"skip {slug}: {md_path} not found")
            continue
        title, body = convert(md_path.read_text())
        page_nav = nav.replace(
            f'data-page="{slug}"', f'data-page="{slug}" class="active"'
        )
        page = TEMPLATE.format(title=esc(title), css=CSS, nav=page_nav, body=body)
        (DOCS / f"{slug}.html").write_text(page)
        print(f"built {slug}.html")


if __name__ == "__main__":
    build()
