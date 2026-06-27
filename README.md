# justOneScript Static Site Generator

A single-script static blog generator written in Python. Inspired by
[bashblog](https://github.com/cfenollosa/bashblog), but with Python,
frontmatter, and Git-based incremental builds.

## Features

- One `.py` file, no framework
- Posts written in Markdown with a YAML-ish frontmatter block
- Incremental builds: only regenerates posts that changed (via `git status`)
- Generates index, tag pages, archive, and RSS feed
- Configurable via a plain `.config.py` file
- Cover images, excerpts, image credits
- External JS support (including the share button)

## Requirements

```
pip install pyyaml markdown
```

Python 3.11+ recommended.

## Installation

```bash
git clone https://github.com/juansemarquez/justonescript-ssg
cd justonescript-ssg
cp .config.example.py .config.py
# edit .config.py with your blog's data
```

## Usage

```bash
# Build only changed posts, then rebuild index/tags/RSS
python justonescript.py build

# Force rebuild all posts
python justonescript.py rebuild

# List all posts
python justonescript.py list

# List all tags
python justonescript.py tags
```

By default, `justonescript.py` looks for `.config.py` in the current directory.
You can override this:

```bash
python justonescript.py build --config /path/to/myconfig.py
```

## Directory layout

```
your-blog/
├── justonescript.py
├── .config.py             ← your settings
├── .config.example.py
├── posts/                 ← your posts go in this folder
│   ├── hello-world.md
│   └── another-post.md
├── assets/                ← static assets go here
│   ├── share.js
│   ├── bootstrap.min.css
│   ├── blog.css
│   └── img/
│       ├── ...
│       └── licenses/
│           ├── cc.svg
│           ├── by.svg
│           ├── nc.svg
│           └── sa.svg
└── output/                ← generated content
    ├── index.html
    ├── hello-world.html
    ├── share.js           ← static assets will be copied on every rebuild
    └── img/
        └── ...
```

Generated files (`*.html`, `feed.rss`) are written to the same directory as
the `.md` files. Add them to `.gitignore` if you track posts in the same repo.

## Writing posts

Each post is a `.md` file with a frontmatter block at the top, delimited by `----`.

### Minimal post

```markdown
----
title: "Mi first post"
pub_date: "2025-06-01 10:00"
tags: ["example", "first"]
----

Post body goes here. Plain **Markdown**.

```

### Full frontmatter reference

```markdown
----
title: "The title of the post"

pub_date: "2025-06-01 10:00"

description: "A one-line excerpt shown on the index page."

description: |
  A multi-paragraph excerpt.

  This is the second paragraph.

description_on_article: true

cover_image: "img/my-photo.png"
cover_caption: "A caption for the cover image"

image_credits:
    - text: "First image"
      url: "https://url1.com"
    - text: "Second image"
      url: "https://url2.com"
tags: ["tag1", "tag2", ...]
----

Post body...

```

### Frontmatter fields

| Field | Required | Description |
|---|---|---|
| `title` | Yes | Post title. Falls back to first line in the body. |
| `pub_date` | No | Publication date (`"YYYY-MM-DD HH:MM"`). Falls back to file mtime. |
| `description` | No | Excerpt shown on index, tag pages, and RSS. Supports Markdown. |
| `description_on_article` | No | `true` to repeat the excerpt at the top of the post. Default: `false`. |
| `cover_image` | No | Path to cover image (relative to the blog root). |
| `cover_caption` | No | Caption shown below the cover image. |
| `image_credits` | No | Credits for images, in order of appearance. Format: YAML list. |
| `tags` | No | Tags for the post. Python list or comma-separated string. |


## Configuration

Copy `.config.example.py` to `.config.py` and edit it. It is a plain Python
file, so you can use variables, expressions, and comments freely.

### Key settings

```python
global_title    = "My Blog"
global_url      = "https://example.com/blog"
global_author   = "Your Name"
global_license  = '<a href="...">CC BY-NC-SA 4.0</a>'

# Number of posts shown on the index page
number_of_index_articles = 10

# CSS files included on every page
css_include = ["bootstrap.min.css", "blog.css"]

# JS files included on every page
# The first file is expected to define the compartir() function
js_include = ["share.js"]

# Posts excluded from the index and tag pages (but still generated)
html_exclude = ["drafts.html"]

# HTML files that are not posts (won't appear anywhere in the blog)
non_blogpost_files = ["about.html", "contact.html"]

# Optional: replace the generated header/footer with your own files
header_file = ""   # e.g. "my-header.html"
footer_file = ""   # e.g. "my-footer.html"

# Optional: inject content around the body
body_begin_file       = ""   # inserted after <body> on every page
body_end_file         = ""   # inserted before </body> on every page
body_begin_file_index = ""   # inserted after body_begin_file, only on index
```

## Incremental builds

When you run `python justonescript.py build`, the script calls `git status` to
find which `.md` files have changed since the last commit. Only those posts are
regenerated. The index, tag pages, archive, and RSS are always rebuilt.

If Git is not available, all posts are rebuilt.

To force a full rebuild regardless of Git:

```bash
python justonescript.py rebuild
```

## Share button

The share button calls a JavaScript function `compartir(url)`. By default this
is expected to live in `share.js`:

```javascript
async function compartir(url) {
    const title = document.title;
    if (navigator.share) {
        try {
            await navigator.share({ title, url });
        } catch (err) {
            console.error("Error sharing:", err);
        }
    } else {
        try {
            await navigator.clipboard.writeText(url);
            alert("URL copied to clipboard:\n" + url);
        } catch (err) {
            alert("Could not copy URL");
        }
    }
}
```

You can add more JS files via `js_include` in your `.config.py`.

## CSS and other static assets

Within the `assets` directory, you can modify/add whatever CSS you want. The
default settings are the ones I use for my blog. Feel free to replace
everything. I tend to download files instead of linking CDNs, but that's up to
you.

The default options are:

- bootstrap (you can replace it for CDN), as explained in
  [https://getbootstrap.com/](https://getbootstrap.com/)
- `blog.css` custom CSS. Delete / replace it by whatever you want. Every css
  you add should be added to the list in `css_include`, in your `.config.py`
file.
- `img` subdirectory has images for licenses and example pictures.
- `share.js` has custom javascript for the "Share" button. You can add as many
custom javascript files as you want via `js_include` in `.config.py`.
- Some code highlighting files, thanks to
  [highlight.js](https://highlightjs.org/). I include the programming languages
I use, but you can add/remove whatever you want.

## License

MIT License. See `LICENSE`.
