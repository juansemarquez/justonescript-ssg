#!/usr/bin/env python3
"""
justonescript.py — Static blog generator, Python rewrite of a custom bashblog fork.
Usage:
    python justonescript.py build   # Build only changed posts + always rebuild index/tags/rss
    python justonescript.py rebuild # Force-rebuild every post
    python justonescript.py list    # List all posts
    python justonescript.py tags    # List all tags

Configuration is read from .config.py
Posts are *.md files with a YAML-ish frontmatter block delimited by ----.
"""

import argparse
import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup # pip install beautifulsoup4
import yaml                   # pip install pyyaml
import markdown               # pip install markdown
                              # also: pip install markdown-extensions  (included in markdown extras)

# ---------------------------------------------------------------------------
# Default configuration
# ---------------------------------------------------------------------------
DEFAULTS = {
    "global_software_name": "JustOneScript SSG",
    "global_software_url": "https://github.com/juansemarquez/justonescript-ssg",
    "global_software_version": "0.1",
    "global_title": "My Blog",
    "global_description": "A blog",
    "global_url": "http://example.com/blog",
    "global_author": "Author",
    "global_author_url": "http://example.com",
    "posts_dir": "posts",
    "output_dir": "output",
    "assets_dir": "assets",
    "global_license": '<a class="text-warning" href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY-NC-SA 4.0</a>'
        '<img src="img/licenses/cc.svg" alt="cc" style="max-width:1em;max-height:1em;margin-left:.2em;">'
        '<img src="img/licenses/by.svg" alt="by" style="max-width:1em;max-height:1em;margin-left:.2em;">'
        '<img src="img/licenses/nc.svg" alt="nc" style="max-width:1em;max-height:1em;margin-left:.2em;">'
        '<img src="img/licenses/sa.svg" alt="sa" style="max-width:1em;max-height:1em;margin-left:.2em;">',
    "global_twitter_username": "",
    "mastodon_account": "",
    "twitter_account": "",
    "instagram_account": "",
    "index_file": "index.html",
    "archive_index": "all_posts.html",
    "tags_index": "all_tags.html",
    "blog_feed": "feed.rss",
    "prefix_tags": "tag_",
    "header_file": "",
    "footer_file": "",
    "body_begin_file": "",
    "body_end_file": "",
    "body_begin_file_index": "",
    "number_of_index_articles": "8",
    "number_of_feed_articles": "10",
    "css_include": ["bootstrap.min.css","blog.css","highlight/default.min.css"],
    "date_format": "%d/%m/%Y",
    "date_locale": "es_AR.UTF-8",
    "non_blogpost_files": [],
    "html_exclude": [],
    # Template strings
    "template_read_more": "Read more...",
    "template_archive": "View more posts",
    "template_archive_title": "All posts",
    "template_tags_title": "All tags",
    "template_tag_title": "Posts tagged",
    "template_archive_index_page": "Back to the index page",
    "template_subscribe": "Subscribe (RSS)",
    "template_subscribe_browser_button": "Subscribe",
    "template_tags_line_header": "Tags:",
    "js_include": [
        "share.js",
        "highlight/highlight.min.js",
        "highlight/bash.min.js",
        "highlight/php.min.js",
        "highlight/python.min.js",
        "highlight/yaml.min.js",
        "highlight/highlightAll.js",
    ],
    "include_share_button": True,
    "template_share_text": "Share",
}

# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def load_config(path=".config.py"):
    cfg = dict(DEFAULTS)

    try:
        spec = importlib.util.spec_from_file_location("blog_config", path)

        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load {path}")

        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

    except FileNotFoundError:
        msg = f"Config file '{path}' not found."

    except PermissionError:
        msg = f"Permission error on '{path}'."

    except SyntaxError as e:
        msg = (
            f"Syntax error in '{path}' "
            f"(line {e.lineno}: {e.msg})."
        )

    except Exception as e:
        msg = f"Error while loading '{path}': {e}"

    else:
        # Overwrite defaults
        for key in DEFAULTS:
            if hasattr(mod, key):
                cfg[key] = getattr(mod, key)
        return cfg

    print(f"ERROR: {msg}", file=sys.stderr)

    respuesta = input(
        "Load default config? [y/N] "
    ).strip().lower()

    if respuesta.lower() in ("s", "si", "sí", "y", "yes"):
        return cfg

    sys.exit(1)

# ---------------------------------------------------------------------------
# Frontmatter parser
# ---------------------------------------------------------------------------

def parse_frontmatter(md_path: Path):
    """
    Returns (frontmatter: dict, body: str, title: str, tags: list[str]).

    File format:
        ----
        key: value
        ----

        Body...

    Fallbacks:
        - If no title is set, takes first line of the body as title
        - If no tags are set, checks if last line of the body is
          "Tags: tag1, tag2, ..."   
    """
    text = md_path.read_text(encoding="utf-8")
    fm = {}
    body = text

    # Detect and strip frontmatter block
    if text.startswith("----"):
        # Find the closing ----
        rest = text[4:]  # skip opening ----
        # skip optional newline right after opening ----
        if rest.startswith("\n"):
            rest = rest[1:]
        end = rest.find("\n----")
        if end != -1:
            fm_text = rest[:end]
            body = rest[end + 5:]   # skip \n----
            if body.startswith("\n"):
                body = body[1:]
            try:
                fm = yaml.safe_load(fm_text) or {}
            except yaml.YAMLError as e:
                print(f"  WARNING: bad frontmatter in {md_path}: {e}")
                fm = {}

    # Title: taking from frontmatter, fallback: first non-empty line of the body
    title=fm.get("title", "").strip()
    title_line_idx = 0
    body_lines = body.split("\n")
    if not title:
        # Fallbacks to first line in the body
        for i, line in enumerate(body_lines):
            if line.strip():
                title = line.strip()
                title_line_idx = i
                break
        # Remove title line from body
        body_without_title = "\n".join(body_lines[title_line_idx + 1:])
    else:
        body_without_title = "\n".join(body_lines)


    # Parsing tags from frontmatter
    tags = []
    if "tags" in fm:
        raw = fm["tags"]
        if isinstance(raw, list):
            tags = [str(t).strip() for t in raw]
        else:
            tags = [t.strip() for t in str(raw).split(",") if t.strip()]
    else:
        # Fallback: last non-empty line that starts with "Tags:"
        body_final_lines = body_without_title.rstrip().split("\n")
        if body_final_lines and re.match(r"^Tags:\s*", body_final_lines[-1], re.IGNORECASE):
            tags_line = body_final_lines[-1]
            tags_raw = re.sub(r"^Tags:\s*", "", tags_line, flags=re.IGNORECASE)
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
            body_without_title = "\n".join(body_final_lines[:-1])

    return fm, body_without_title, title, tags


# ---------------------------------------------------------------------------
# Markdown → HTML
# ---------------------------------------------------------------------------

def md_to_html(md_text: str) -> str:
    """Convert Markdown to HTML using the `markdown` library with useful extensions."""
    return markdown.markdown(
        md_text,
        extensions=["fenced_code", "tables", "attr_list", "def_list", "footnotes", "sane_lists"],
    )

# ---------------------------------------------------------------------------
# Git-based change detection
# ---------------------------------------------------------------------------

def git_changed_files(pattern="*.md") -> set[str]:
    """
    Return set of *.md filenames that git considers modified or untracked
    since their last committed version.  Falls back to 'all files' if git
    is not available or the directory is not a repo.
    """
    try:
        # Modified / new in working tree vs HEAD
        result = subprocess.run(
            ["git", "status", "--porcelain", "--", pattern],
            capture_output=True, text=True, check=True,
        )
        changed = set()
        for line in result.stdout.splitlines():
            # porcelain format: XY filename
            fname = line[3:].strip()
            # handle renames: "old -> new"
            if " -> " in fname:
                fname = fname.split(" -> ")[-1]
            changed.add(fname)
            changed.add(Path(fname).name)
        return changed
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None   # caller will treat None as "rebuild everything"


def file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# HTML building blocks
# ---------------------------------------------------------------------------

def load_or_build_head(cfg: dict, page_title: str, twitter_meta: str = "") -> str:
    header_file = cfg.get("header_file", "")
    if header_file and Path(header_file).exists():
        return Path(header_file).read_text(encoding="utf-8")
    return build_head(cfg, page_title, twitter_meta)

def build_head(cfg: dict, page_title: str, twitter_meta: str = "") -> str:
    css_links = ""
    css_list = cfg["css_include"] if isinstance(cfg["css_include"], list) else cfg["css_include"].split()
    for css in css_list:
        css_links += f'<link rel="stylesheet" href="{css}" type="text/css" />\n'

    js_files = cfg.get("js_include", [])
    if isinstance(js_files, str):
        js_files = js_files.split()
    js_tags = "".join(f'<script defer src="{f}"></script>\n' for f in js_files)

    return (
        "<!DOCTYPE html>\n<html><head>\n"
        '<meta charset="UTF-8" />\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0" />\n'
        + css_links
        + f'<link rel="alternate" type="application/rss+xml" '
        f'title="{cfg["template_subscribe_browser_button"]}" href="{cfg["blog_feed"]}" />\n'
        + twitter_meta
        + f"<title>{page_title}</title>\n"
        + js_tags
        + "\n</head>"
    )

def build_site_header(cfg: dict) -> str:
    social = ""
    if cfg.get("mastodon_account"):
        social += f'<a href="{cfg["mastodon_account"]}" target="_blank" class="social" title="Mastodon"><img src="img/mastodon.png"></a>\n'
    if cfg.get("twitter_account"):
        social += f'<a href="{cfg["twitter_account"]}" target="_blank" class="social" title="Twitter"><img src="img/twitter.png"></a>\n'
    if cfg.get("instagram_account"):
        social += f'<a href="{cfg["instagram_account"]}" target="_blank" class="social" title="Instagram"><img src="img/instagram.png"></a>\n'

    return (
        '<div id="divbodyholder" class="md-cols-8 md-offset-2 lg-cols-6 lg-offset-6 cols-12">\n'
        '<div class="headerholder jumbotron text-center"><div class="header">\n'
        '<div id="title">\n'
        f'<h1 class="nomargin"><a class="ablack" href="{cfg["global_url"]}/{cfg["index_file"]}">'
        f'{cfg["global_title"]}</a></h1>\n'
        f'<div id="description"><em>{cfg["global_description"]}</em></div>\n'
        f'<div id="social" class="text-right">\n{social}</div>\n'
        "</div></div></div>\n"
        '<div id="divbody" class="p-4"><div class="content">\n'
    )

def load_or_build_footer(cfg: dict) -> str:
    footer_file = cfg.get("footer_file", "")
    if footer_file and Path(footer_file).exists():
        return Path(footer_file).read_text(encoding="utf-8")
    return build_footer(cfg)

def build_footer(cfg: dict) -> str:
    software_name = cfg.get('global_software_name', 'JustOneScript SSG');
    software_url = cfg.get('global_software_url', 'https://github.com/juansemarquez/justonescript-ssg');
    return (
        f'<div id="footer" class=\'text-center small text-light bg-dark\'>'
        f'{cfg["global_license"]}\n'
        f'<a href="{cfg["global_author_url"]}" class="text-warning">{cfg["global_author"]}</a><br/>\n'
        "Generated with \n"
        f'<a href="{software_url}" class="text-warning">{software_name}</a>.</div>\n'
        "</div></div></div>\n</body></html>"
    )


def build_twitter_card(cfg: dict, title: str, description: str, image_url: str = "") -> str:
    if not cfg.get("global_twitter_username"):
        return ""
    desc_escaped = description.replace('"', "'")[:250]
    meta = (
        "<meta name='twitter:card' content='summary' />\n"
        f"<meta name='twitter:site' content='@{cfg['global_twitter_username']}' />\n"
        f"<meta name='twitter:title' content='{title}' />\n"
        f'<meta name=\'twitter:description\' content="{desc_escaped}" />\n'
    )
    if image_url:
        if not image_url.startswith("http"):
            image_url = f"{cfg['global_url']}/{image_url}"
        meta += f"<meta name='twitter:image' content='{image_url}' />\n"
    return meta


def share_button(url: str, share_text: str) -> str:
    return (
        f"<p id='twitter'>\n"
        f"<button class='btn btn-primary' onclick='compartir(\"{url}\");'>"
        f"{share_text}</button></p>\n"
    )


# ---------------------------------------------------------------------------
# Cover image block
# ---------------------------------------------------------------------------

def build_cover_block(fm: dict) -> str:
    cover = fm.get("cover_image", "")
    if not cover:
        return ""
    caption = fm.get("cover_caption", "")
    html = '<div class="figure"><figure>\n'
    html += f'<img src="{cover}" alt="{caption}" />\n'
    if caption and caption != "alt":
        html += f"<figcaption>\n{caption}\n</figcaption>\n"
    html += "</figure></div>\n"
    return html


# ---------------------------------------------------------------------------
# Image credits block
# ---------------------------------------------------------------------------

def build_credits_block(fm: dict, cfg :dict) -> str:
    credits = fm.get("image_credits", [])
    if not credits:
        return ""

    items = []
    for item in credits:
        if isinstance(item, dict):
            text = item.get("text", "")
            url = item.get("url", "")
            if url:
                items.append(f'<a href="{url}">{text}</a>')
            else:
                items.append(text)
        else:
            # fallback: plain string
            items.append(str(item))

    if len(items) == 1:
        msg = cfg.get("template_image_credits_singular", "Image credits") + ": "
    else:
        msg = cfg.get("template_image_credits_plural", "Image credits") + ": "
    return "<p><small>" + msg + " &mdash; ".join(items) + "</small></p>\n"

# ---------------------------------------------------------------------------
# Parse pub_date from frontmatter
# ---------------------------------------------------------------------------

def parse_pub_date(fm: dict, md_path: Path, cfg: dict) -> datetime:
    raw = fm.get("pub_date", "")
    if raw:
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(str(raw).strip('"'), fmt)
                # Assume local timezone
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    # Fallback: file mtime
    mtime = md_path.stat().st_mtime
    return datetime.fromtimestamp(mtime, tz=timezone.utc)


def fmt_date(dt: datetime, cfg: dict) -> str:
    """Format date for display."""
    return dt.strftime(cfg["date_format"])


def fmt_date_rss(dt: datetime) -> str:
    return format_datetime(dt)


# ---------------------------------------------------------------------------
# Boilerplate file detection
# ---------------------------------------------------------------------------

def is_boilerplate(filename: str, cfg: dict) -> bool:
    boilerplate = {
        cfg["index_file"],
        cfg["archive_index"],
        cfg["tags_index"],
        cfg["blog_feed"],
    }
    if filename in boilerplate:
        return True
    if filename.startswith(cfg["prefix_tags"]):
        return True
    # non_blogpost_files: .html files that are not posts (about, contact, etc.)
    non_posts = cfg.get("non_blogpost_files", [])
    if isinstance(non_posts, str):
        non_posts = non_posts.split()
    if filename in non_posts:
        return True
    return False


# ---------------------------------------------------------------------------
# Slug generation from title
# ---------------------------------------------------------------------------

def title_to_slug(title: str) -> str:
    """Convert a post title to a URL-safe filename (without extension)."""
    import unicodedata
    # Normalize unicode → ASCII approximation
    nfkd = unicodedata.normalize("NFKD", title)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    slug = ascii_str.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "post"

# ---------------------------------------------------------------------------
# Surround img with figure
# ---------------------------------------------------------------------------

def surround_img_with_figure(html_content: str) -> str:
    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find every <img>
    for img in soup.find_all('img'):
        # Verify if it's already in <figure>
        if img.find_parent('figure'):
            continue

        # Creating new <figure> and <figcaption>
        new_div = soup.new_tag('div', attrs={"class": "figure"})
        new_figure = soup.new_tag('figure')

        # Extracting 'alt' text for figcaption (if any)
        alt_text = img.get('alt', '')
        if alt_text and alt_text != "alt":
            new_figcaption = soup.new_tag('figcaption')
            new_figcaption.string = alt_text
        else:
            new_figcaption = None

        # Replacing img for figure withing div within HTML
        img.replace_with(new_div)
        new_div.append(new_figure)

        # Appending img to figure
        new_figure.append(img)

        # If there is a figcaption, appending int within figure after the image
        if new_figcaption:
            new_figure.append(new_figcaption)

    # Returnig modified HTML as a string
    return str(soup)

def optional_file_content(path: str) -> str:
    if path and Path(path).exists():
        return Path(path).read_text(encoding="utf-8")
    return ""

# ---------------------------------------------------------------------------
# Build a single post HTML
# ---------------------------------------------------------------------------

def build_post_html(
    cfg: dict,
    md_path: Path,
    out_path: Path,
    fm: dict,
    body_md: str,
    title: str,
    tags: list[str],
    pub_date: datetime,
):
    """Render one post and write it to out_path."""

    slug = out_path.name 
    post_url = f"{cfg['global_url']}/{slug}"

    # Description / excerpt
    description_md = fm.get("description", "")
    if isinstance(description_md, list):
        description_md = "\n".join(description_md)
    description_md = str(description_md).strip()
    description_html = md_to_html(description_md) if description_md else ""

    description_on_article = fm.get("description_on_article", False)

    # Body HTML
    body_html = md_to_html(body_md)
    body_html = surround_img_with_figure(body_html)

    # Cover
    cover_html = build_cover_block(fm)

    # Tags line
    tags_html = ""
    if tags:
        tag_links = ", ".join(
            f"<a href='{cfg['prefix_tags']}{t}.html'>{t}</a>" for t in tags
        )
        tags_html = f"<p>{cfg['template_tags_line_header']} {tag_links}</p>\n"

    # Credits
    credits_html = build_credits_block(fm, cfg)

    # Twitter card — use plain-text description
    plain_desc = re.sub(r"<[^>]+>", "", description_html).replace("\n", " ")
    cover_image = fm.get("cover_image", "")
    twitter_meta = build_twitter_card(cfg, title, plain_desc, cover_image)

    date_str = fmt_date(pub_date, cfg)
    author = cfg["global_author"]

    head = load_or_build_head(cfg, title, twitter_meta)
    site_header = build_site_header(cfg)
    footer = load_or_build_footer(cfg)

    content_parts = []
    # Description at top of article (if requested)
    if description_on_article and description_html:
        content_parts.append(description_html)
    # Cover image
    if cover_html:
        content_parts.append(cover_html)
    # HR separator (between cover/description and body)
    if description_html or cover_html:
        content_parts.append("<hr />\n")
    # Main body
    content_parts.append(body_html)
    # Credits
    if credits_html:
        content_parts.append(credits_html)
    # Tags
    content_parts.append(tags_html)

    content_html = "".join(content_parts)

    body_begin = optional_file_content(cfg.get("body_begin_file", ""))
    body_end = optional_file_content(cfg.get("body_end_file", ""))

    share_button_code = ""
    if cfg["include_share_button"]:
        share_button_code = share_button(post_url, cfg["template_share_text"])

    html = (
        head
        + "\n<body class=container>\n"
        + site_header
        + body_begin
        + "<!-- entry begin -->\n"
        + f'<h3><a class="ablack" href="{slug}">\n{title}\n</a></h3>\n'
        + f"<!-- bashblog_timestamp: #{pub_date.strftime('%Y%m%d%H%M.%S')}# -->\n"
        + f'<div class="subtitle">{date_str} &mdash; \n{author}\n</div>\n'
        + "<!-- text begin -->\n"
        + content_html
        + "\n<!-- text end -->\n"
        + share_button_code
        + "<!-- entry end -->\n"
        + "</div>\n"
        + body_end
        + footer
    )

    out_path.write_text(html, encoding="utf-8")
    print(f"  wrote {out_path}")


# ---------------------------------------------------------------------------
# Excerpt for index / RSS (description from frontmatter, or first paragraph)
# ---------------------------------------------------------------------------

def get_excerpt_html(fm: dict, body_md: str) -> str:
    description_md = fm.get("description", "")
    if isinstance(description_md, list):
        description_md = "\n".join(description_md)
    description_md = str(description_md).strip()
    if description_md:
        return md_to_html(description_md)
    # Fallback: first paragraph of body
    paras = [p.strip() for p in body_md.split("\n\n") if p.strip()]
    if paras:
        return md_to_html(paras[0])
    return ""


# ---------------------------------------------------------------------------
# Index entry snippet (used in index.html and tag pages)
# ---------------------------------------------------------------------------

def build_index_entry(cfg: dict, slug: str, title: str, date_str: str, excerpt_html: str, cover_html: str) -> str:
    post_url = f"{cfg['global_url']}/{slug}"
    read_more = f'<p class="readmore"><br><a href="./{slug}">{cfg["template_read_more"]}</a></p>\n'

    entry = (
        f'<h3><a class="ablack" href="{slug}">\n{title}\n</a></h3>\n'
        f"<!-- bashblog_timestamp: # -->\n"
        f'<div class="subtitle">{date_str} &mdash; \n{cfg["global_author"]}\n</div>\n'
        "<!-- text begin -->\n"
    )
    if excerpt_html:
        entry += excerpt_html + "\n"
    if cover_html:
        entry += cover_html + "\n"
    entry += read_more

    if cfg["include_share_button"]:
        entry += share_button(post_url, cfg["template_share_text"])

    return entry

# ---------------------------------------------------------------------------
# Detect files excluded from index
# ---------------------------------------------------------------------------

def is_excluded_from_index(slug: str, cfg: dict) -> bool:
    excluded = cfg.get("html_exclude", [])
    if isinstance(excluded, str):
        excluded = excluded.split()
    return slug in excluded

# ---------------------------------------------------------------------------
# Outputs to the folder specified in the config
# ---------------------------------------------------------------------------

def out(cfg: dict, filename: str) -> Path:
    d = Path(cfg.get("output_dir", "output"))
    d.mkdir(parents=True, exist_ok=True)
    return d / filename

# ---------------------------------------------------------------------------
# Collect all posts metadata
# ---------------------------------------------------------------------------

def collect_posts(cfg: dict) -> list[dict]:
    """
    Scan *.md files, parse frontmatter, return list of post dicts sorted
    newest-first by pub_date.
    """
    posts = []
    posts_dir = Path(cfg.get("posts_dir", "posts"))
    for md_path in sorted(posts_dir.glob("*.md")):
        fm, body_md, title, tags = parse_frontmatter(md_path)
        if not title:
            continue
        pub_date = parse_pub_date(fm, md_path, cfg)
        slug_base = title_to_slug(title)
        slug = slug_base + ".html"
        # Avoid collisions — deterministic: use md stem if it already looks like a slug
        if md_path.stem != md_path.stem.replace(" ", "-"):
            slug = md_path.stem + ".html"
        posts.append(
            {
                "md_path": md_path,
                "slug": slug,
                "title": title,
                "tags": tags,
                "pub_date": pub_date,
                "fm": fm,
                "body_md": body_md,
                "date_str": fmt_date(pub_date, cfg),
            }
        )
    posts.sort(key=lambda p: p["pub_date"], reverse=True)
    return posts


# ---------------------------------------------------------------------------
# Build index.html
# ---------------------------------------------------------------------------

def build_index(cfg: dict, posts: list[dict]):
    n = int(cfg["number_of_index_articles"])
    selected = [p for p in posts if not is_excluded_from_index(p["slug"], cfg)][:n]

    # Twitter card: use first post description
    twitter_meta = ""
    if selected:
        p = selected[0]
        plain = re.sub(r"<[^>]+>", "", get_excerpt_html(p["fm"], p["body_md"])).replace("\n", " ")[:250]
        twitter_meta = build_twitter_card(cfg, cfg["global_title"], plain)

    head = load_or_build_head(cfg, cfg["global_title"], twitter_meta)
    site_header = build_site_header(cfg)
    footer = load_or_build_footer(cfg)

    entries = ""
    for p in selected:
        excerpt_html = get_excerpt_html(p["fm"], p["body_md"])
        cover_html = build_cover_block(p["fm"])
        entries += build_index_entry(
            cfg, p["slug"], p["title"], p["date_str"], excerpt_html, cover_html
        )

    feed = cfg["blog_feed"]
    nav = (
        f'<div id="all_posts">'
        f'<a href="{cfg["archive_index"]}">{cfg["template_archive"]}</a>'
        f' &mdash; <a href="{cfg["tags_index"]}">{cfg["template_tags_title"]}</a>'
        f' &mdash; <a href="{feed}">{cfg["template_subscribe"]}</a>'
        f"</div>\n"
    )

    body_begin = optional_file_content(cfg.get("body_begin_file", ""))
    body_begin_index = optional_file_content(cfg.get("body_begin_file_index", ""))
    body_end = optional_file_content(cfg.get("body_end_file", ""))

    html = (
        head
        + "\n<body class=container>\n"
        + site_header
        + body_begin_index
        + entries
        + "\n\n<!-- Other posts here -->\n\n"
        + nav
        + "</div>\n"
        + body_end
        + footer
    )

    out(cfg, cfg["index_file"]).write_text(html, encoding="utf-8")
    print(f"  wrote {cfg['index_file']}")


# ---------------------------------------------------------------------------
# Build all_posts.html
# ---------------------------------------------------------------------------

def build_all_posts(cfg: dict, posts: list[dict]):
    head = load_or_build_head(cfg, f"{cfg['global_title']} — {cfg['template_archive_title']}")
    site_header = build_site_header(cfg)
    footer = load_or_build_footer(cfg)

    body = f"<h3>{cfg['template_archive_title']}</h3>\n"
    current_month = ""
    open_ul = False
    for p in posts:
        month = p["pub_date"].strftime(cfg.get("date_allposts_header", "%B %Y"))
        if month != current_month:
            if open_ul:
                body += "</ul>\n"
            body += f"<h4 class='allposts_header'>{month}</h4>\n<ul>\n"
            current_month = month
            open_ul = True
        body += f'<li><a href="{p["slug"]}">{p["title"]}</a> &mdash; {p["date_str"]}</li>\n'
    if open_ul:
        body += "</ul>\n"
    body += f'<div id="all_posts"><a href="./{cfg["index_file"]}">{cfg["template_archive_index_page"]}</a></div>\n'

    html = (
        head
        + "\n<body class=container>\n"
        + site_header
        + body
        + "</div>\n"
        + footer
    )
    out(cfg, cfg["archive_index"]).write_text(html, encoding="utf-8")
    print(f"  wrote {cfg['archive_index']}")


# ---------------------------------------------------------------------------
# Build tag pages and all_tags.html
# ---------------------------------------------------------------------------

def build_tags(cfg: dict, posts: list[dict], changed_tags: set = None):
    # Group posts by tag
    tag_posts: dict[str, list[dict]] = {}
    for p in posts:
        for tag in p["tags"]:
            tag_posts.setdefault(tag, []).append(p)

    # Individual tag pages
    for tag, tposts in tag_posts.items():
        if changed_tags is not None and tag not in changed_tags:
            print(f"  skipping tag_{tag}.html (unchanged)")
            continue
        head = load_or_build_head(cfg, f"{cfg['global_title']} — {cfg['template_tag_title']} \"{tag}\"")
        site_header = build_site_header(cfg)
        footer = load_or_build_footer(cfg)

        entries = ""
        for p in tposts:
            excerpt_html = get_excerpt_html(p["fm"], p["body_md"])
            cover_html = build_cover_block(p["fm"])
            entries += build_index_entry(
                cfg, p["slug"], p["title"], p["date_str"], excerpt_html, cover_html
            )

        html = (
            head
            + "\n<body class=container>\n"
            + site_header
            + entries
            + "</div>\n"
            + footer
        )
        tag_file = f"{cfg['prefix_tags']}{tag}.html"
        out(cfg, tag_file).write_text(html, encoding="utf-8")
        print(f"  wrote {tag_file}")

    # all_tags.html
    head = load_or_build_head(cfg, f"{cfg['global_title']} - {cfg['template_tags_title']}")
    site_header = build_site_header(cfg)
    footer = load_or_build_footer(cfg)

    body = f"<h3>{cfg['template_tags_title']}</h3>\n<ul>\n"
    for tag in sorted(tag_posts):
        n = len(tag_posts[tag])
        word = "post" if n == 1 else "posts"
        body += f'<li><a href="{cfg["prefix_tags"]}{tag}.html">{tag}</a> &mdash; {n} {word}</li>\n'
    body += "</ul>\n"
    body += f'<div id="all_posts"><a href="./{cfg["index_file"]}">{cfg["template_archive_index_page"]}</a></div>\n'

    html = (
        head
        + "\n<body class=container>\n"
        + site_header
        + body
        + "</div>\n"
        + footer
    )
    out(cfg, cfg["tags_index"]).write_text(html, encoding="utf-8")
    print(f"  wrote {cfg['tags_index']}")


# ---------------------------------------------------------------------------
# Build RSS feed
# ---------------------------------------------------------------------------

def build_rss(cfg: dict, posts: list[dict]):
    n = int(cfg["number_of_feed_articles"])
    selected = posts[:n]

    pub_date_rss = fmt_date_rss(datetime.now(tz=timezone.utc))

    items = ""
    for p in selected:
        excerpt_html = get_excerpt_html(p["fm"], p["body_md"])
        body_html = md_to_html(p["body_md"])
        content = (excerpt_html + "\n" + body_html) if excerpt_html else body_html
        post_url = f"{cfg['global_url']}/{p['slug']}"
        item_date = fmt_date_rss(p["pub_date"])
        # Escape for CDATA is not needed — CDATA handles it
        items += (
            f"<item>\n"
            f"  <title>{p['title']}</title>\n"
            f"  <description><![CDATA[{content}]]></description>\n"
            f"  <link>{post_url}</link>\n"
            f"  <guid>{post_url}</guid>\n"
            f"  <dc:creator>{cfg['global_author']}</dc:creator>\n"
            f"  <pubDate>{item_date}</pubDate>\n"
            f"</item>\n"
        )

    rss = (
        '<?xml version="1.0" encoding="UTF-8" ?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        "<channel>\n"
        f"  <title>{cfg['global_title']}</title>\n"
        f"  <link>{cfg['global_url']}/{cfg['index_file']}</link>\n"
        f"  <description>{cfg['global_description']}</description>\n"
        f"  <language>es</language>\n"
        f"  <lastBuildDate>{pub_date_rss}</lastBuildDate>\n"
        f"  <pubDate>{pub_date_rss}</pubDate>\n"
        f'  <atom:link href="{cfg["global_url"]}/{cfg["blog_feed"]}" rel="self" type="application/rss+xml" />\n'
        + items
        + "</channel>\n</rss>\n"
    )

    out(cfg, cfg["blog_feed"]).write_text(rss, encoding="utf-8")
    print(f"  wrote {cfg['blog_feed']}")

# ---------------------------------------------------------------------------
# Copy assets to output file
# ---------------------------------------------------------------------------

def copy_assets(cfg: dict):
    src = Path(cfg.get("assets_dir", "assets"))
    dst = Path(cfg.get("output_dir", "output"))

    if not src.exists():
        print(f"  assets_dir '{src}' not found, skipping.")
        return

    for item in src.iterdir():
        s = src / item.name
        d = dst / item.name
        if s.is_dir():
            if d.exists():
                shutil.rmtree(d)
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)

    print(f"  copied assets from {src}/ → {dst}/")

# ---------------------------------------------------------------------------
# Main build logic
# ---------------------------------------------------------------------------

def cmd_build(cfg: dict, force: bool = False):
    print("Collecting posts...")
    posts = collect_posts(cfg)

    if force:
        changed_md = None   # rebuild all
        print("  Force rebuild — processing all posts.")
    else:
        changed_md = git_changed_files("*.md")
        if changed_md is None:
            print("  Git not available — processing all posts.")
        else:
            print(f"  Git reports {len(changed_md)} changed/new .md file(s).")

    built = 0
    changed_tags = set()
    for p in posts:
        slug = p["slug"]
        out_path = out(cfg, slug)
        md_path = p["md_path"]

        needs_build = (
            force
            or changed_md is None
            or md_path.name in changed_md
            or not out_path.exists()
        )

        if needs_build:
            print(f"  building {slug} ← {md_path.name}")
            build_post_html(
                cfg,
                md_path,
                out_path,
                p["fm"],
                p["body_md"],
                p["title"],
                p["tags"],
                p["pub_date"],
            )
            built += 1
            changed_tags.update(p["tags"])
        else:
            print(f"  skipping {slug} (unchanged)")

    print(f"\nBuilt {built} post(s). Rebuilding index, tags, RSS...")
    build_index(cfg, posts)
    build_all_posts(cfg, posts)
    build_tags(cfg, posts, changed_tags=changed_tags)
    build_rss(cfg, posts)
    copy_assets(cfg)
    print("Done.")


def cmd_list(cfg: dict):
    posts = collect_posts(cfg)
    if not posts:
        print("No posts found.")
        return
    for i, p in enumerate(posts, 1):
        print(f"  {i:3}. [{p['date_str']}] {p['title']}  →  {p['slug']}")


def cmd_tags(cfg: dict):
    posts = collect_posts(cfg)
    tag_counts: dict[str, int] = {}
    for p in posts:
        for t in p["tags"]:
            tag_counts[t] = tag_counts.get(t, 0) + 1
    if not tag_counts:
        print("No tags found.")
        return
    for tag in sorted(tag_counts):
        print(f"  {tag}  ({tag_counts[tag]} post{'s' if tag_counts[tag] != 1 else ''})")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Static blog generator")
    parser.add_argument(
        "command",
        choices=["build", "rebuild", "list", "tags"],
        help="Command to run",
    )
    parser.add_argument("--config", default=".config.py", help="Config file path (default: .config)")
    args = parser.parse_args()

    cfg = load_config(args.config)

    if args.command == "build":
        cmd_build(cfg, force=False)
    elif args.command == "rebuild":
        cmd_build(cfg, force=True)
    elif args.command == "list":
        cmd_list(cfg)
    elif args.command == "tags":
        cmd_tags(cfg)


if __name__ == "__main__":
    main()
