global_software_name="JustOneScript SSG"
global_software_url="https://github.com/juansemarquez/justonescript-ssg"
global_software_version="0.1"

# Blog title
global_title="Your blog title"
# The typical subtitle for each blo
global_description= "Subtitle of your blog"
# The public base URL for this blog
global_url="http://example.com"

# Your name
global_author="Your name"
# You can use twitter or facebook or anything for global_author_url
global_author_url="http://your-url.com.ar"

# Directory where your .md files (your posts) live
posts_dir="posts"
# Directory where the generated site will be written
output_dir="output"
# Directory with static assets that will be copied to your site
assets_dir="assets"

# CC by-nc is a good starting point, you can change this to "&copy;" for Copyright
global_license='<a class="text-warning" href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY-NC-SA 4.0</a><img src="img/licenses/cc.svg" alt="cc" style="max-width: 1em;max-height:1em;margin-left: .2em;"><img src="img/licenses/by.svg" alt="by" style="max-width: 1em;max-height:1em;margin-left: .2em;"><img src="img/licenses/nc.svg" alt="nc" style="max-width: 1em;max-height:1em;margin-left: .2em;"><img src="img/licenses/sa.svg" alt="sa" style="max-width: 1em;max-height:1em;margin-left: .2em;">'

# Change this to your username if you want to use twitter for comments
global_twitter_username=""

mastodon_account="https://your-mastodon-instance.com/@your_account"
twitter_account="https://twitter.com/your-account"
instagram_account="https://www.instagram.com/your-account/"

# Blog generated files
# index page of blog (it is usually good to use "index.html" here)
index_file="index.html"
number_of_index_articles="50"
# global archive
archive_index="all_posts.html"
tags_index="all_tags.html"

# Non blogpost files. Will be ignored. Useful for static pages and custom
# content
# Add them as a list array, e.g. non_blogpost_files=["news.html" "test.html"]
non_blogpost_files=[]

# feed file (rss in this case)
blog_feed="feed.rss"
number_of_feed_articles="10"
# prefix for tags/categories files
# please make sure that no other html file starts with this prefix
prefix_tags="tag_"
# personalized header and footer (only if you know what you're doing)
# DO NOT name them .header.html, .footer.html or they will be overwritten
# leave blank to generate them, recommended
header_file=""
footer_file=""
# extra content to add just after we open the <body> tag
# and before the actual blog content
body_begin_file=""
# extra content to add just before we close </body>
body_end_file=""
# extra content to ONLY on the index page AFTER `body_begin_file` contents
# and before the actual content
body_begin_file_index=""
# CSS files to include on every page, f.ex. css_include=['main.css','blog.css']
# leave empty to use generated
css_include=['main.css', 'blog.css', 'highlight/default.min.css']

# javascript files to be included in every page
js_include = [
        "share.js",
        "highlight/highlight.min.js",
        "highlight/bash.min.js",
        "highlight/php.min.js",
        "highlight/python.min.js",
        "highlight/yaml.min.js",
        "highlight/highlightAll.js",
]

# HTML files to exclude from index, f.ex. post_exclude=['imprint.html','aboutme.html']
html_exclude=[]

# Localization and i18n
# "Read more..." (link under cut article on index page)
template_read_more="Read more..."
# "View more posts" (used on bottom of index page as link to archive)
template_archive="View more posts"
# "All posts" (title of archive page)
template_archive_title="All posts"
# "All tags"
template_tags_title="All tags"
# "posts" (on "All tags" page, text at the end of each tag line, like "2. Music - 15 posts")
template_tags_posts="posts"
template_tags_posts_2_4="posts"  # Some slavic languages use a different plural form for 2-4 items
template_tags_posts_singular="post"
# "Posts tagged" (text on a title of a page with index of one tag, like "My Blog - Posts tagged "Music"")
template_tag_title="Posts tagged"
# "Tags:" (beginning of line in HTML file with list of all tags for this article)
template_tags_line_header="Tags:"
# "Back to the index page" (used on archive page, it is link to blog index)
template_archive_index_page="Back to the index page"
# "Subscribe" (used on bottom of index page, it is link to RSS feed)
template_subscribe="Subscribe (RSS)"
# "Subscribe to this page..." (used as text for browser feed button that is embedded to html)
template_subscribe_browser_button="Subscribe"
# "Image credits" text, singular and plural
template_image_credits_singular="Image credits"
template_image_credits_plural="Image credits"

# Text to be shown in the "Share" button
template_share_text = "Share"

# The locale to use for the dates displayed on screen
date_format="%d/%m/%Y"
date_locale="es_AR"
# Don't change these dates
date_format_full="%a, %d %b %Y %H:%M:%S %z"
date_format_timestamp="%Y%m%d%H%M.%S"
date_allposts_header="%B %Y"
