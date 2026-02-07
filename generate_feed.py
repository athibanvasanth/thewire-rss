import datetime
import html
import os
import re
import shutil

import requests

WP_API = "https://cms.thewire.in/wp-json/wp/v2/posts"
WP_CATEGORIES_API = "https://cms.thewire.in/wp-json/wp/v2/categories"
SITE_URL = "https://thewire.in"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "TheWireRSS/1.0"})
FEED_TITLE = "The Wire"
FEED_DESCRIPTION = (
    "The Wire - Independent journalism from India covering politics, "
    "economy, science, law, society, culture, and more."
)
OUT_DIR = os.path.join(os.path.dirname(__file__), "public")


def strip_html(text):
    return re.sub(r"<[^>]+>", "", text).strip()


def extract_first_image(html_content):
    """Extract the first img src from HTML content as a fallback thumbnail."""
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html_content)
    if match:
        return match.group(1)
    return None


def clean_content(html_content):
    """Clean WordPress content for proper RSS display."""
    # Remove script tags and their content
    html_content = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL)
    # Remove noscript tags
    html_content = re.sub(r"<noscript[^>]*>.*?</noscript>", "", html_content, flags=re.DOTALL)
    # Remove inline style tags
    html_content = re.sub(r"<style[^>]*>.*?</style>", "", html_content, flags=re.DOTALL)
    # Remove data-* attributes (WP clutter)
    html_content = re.sub(r'\s+data-\w+="[^"]*"', "", html_content)
    # Remove loading="lazy" and decoding="async" (not needed in feeds)
    html_content = re.sub(r'\s+(?:loading|decoding)="[^"]*"', "", html_content)
    # Remove srcset and sizes attributes (causes clutter, src is enough)
    html_content = re.sub(r'\s+srcset="[^"]*"', "", html_content)
    html_content = re.sub(r'\s+sizes="[^"]*"', "", html_content)
    # Clean up excessive whitespace
    html_content = re.sub(r"\n{3,}", "\n\n", html_content)
    return html_content.strip()


def escape_xml(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def format_rfc822(dt_str):
    dt = datetime.datetime.fromisoformat(dt_str)
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0530")


def fetch_posts(count=30, category_id=None):
    params = {
        "per_page": count,
        "_embed": "author,wp:term,wp:featuredmedia",
        "orderby": "date",
        "order": "desc",
    }
    if category_id:
        params["categories"] = category_id
    resp = SESSION.get(WP_API, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_categories():
    """Fetch top-level categories from The Wire."""
    params = {"per_page": 100, "orderby": "count", "order": "desc"}
    resp = SESSION.get(WP_CATEGORIES_API, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def build_rss(posts, feed_url, base_url="", title=FEED_TITLE, description=FEED_DESCRIPTION):
    now = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S +0000"
    )

    items = []
    for post in posts:
        post_title = escape_xml(html.unescape(post["title"]["rendered"]))
        link = escape_xml(post["link"])
        pub_date = format_rfc822(post["date"])
        post_description = escape_xml(
            strip_html(html.unescape(post["excerpt"]["rendered"]))
        )
        content = post["content"]["rendered"]
        guid = escape_xml(post["guid"]["rendered"])

        author = "The Wire"
        embedded = post.get("_embedded", {})
        authors = embedded.get("author", [])
        if authors and authors[0].get("name"):
            author = escape_xml(authors[0]["name"])

        # Extract featured image for thumbnail and hero image
        thumbnail_xml = ""
        hero_html = ""
        featured_media = embedded.get("wp:featuredmedia", [])
        if featured_media and featured_media[0].get("source_url"):
            fm = featured_media[0]
            img_url = fm["source_url"]
            mime_type = fm.get("mime_type", "image/jpeg")
            alt_text = fm.get("alt_text", "")
            caption_html = fm.get("caption", {}).get("rendered", "")
            caption_text = strip_html(caption_html) if caption_html else ""
            # Thumbnail for RSS reader list view (both tags for broad reader support)
            escaped_img = escape_xml(img_url)
            thumbnail_xml = (
                f'      <media:content url="{escaped_img}" medium="image" type="{mime_type}"/>\n'
                f'      <media:thumbnail url="{escaped_img}"/>\n'
                f'      <enclosure url="{escaped_img}" type="{mime_type}" length="0"/>\n'
            )
            # Hero image at top of content, matching The Wire's layout
            hero_html = f'<figure style="margin:0 0 1.5em 0;"><img src="{img_url}" alt="{alt_text}" style="max-width:100%;height:auto;display:block;"/>'
            if caption_text:
                hero_html += f'<figcaption style="font-size:0.85em;color:#666;margin-top:0.4em;">{caption_text}</figcaption>'
            hero_html += "</figure>\n"
        else:
            # Use The Wire logo as fallback thumbnail so RSS readers
            # don't render an empty image preview placeholder.
            placeholder_url = f"{base_url}/placeholder.png" if base_url else "placeholder.png"
            escaped_ph = escape_xml(placeholder_url)
            thumbnail_xml = (
                f'      <media:content url="{escaped_ph}" medium="image" type="image/png"/>\n'
                f'      <media:thumbnail url="{escaped_ph}"/>\n'
                f'      <enclosure url="{escaped_ph}" type="image/png" length="0"/>\n'
            )

        # Clean and prepare the article content
        content = clean_content(content)
        full_content = hero_html + content

        categories_xml = ""
        terms = embedded.get("wp:term", [])
        if terms:
            for term_group in terms:
                for term in term_group:
                    if term.get("taxonomy") == "category":
                        cat_name = escape_xml(html.unescape(term["name"]))
                        categories_xml += (
                            f"      <category>{cat_name}</category>\n"
                        )

        items.append(
            f"""    <item>
      <title>{post_title}</title>
      <link>{link}</link>
      <guid isPermaLink="false">{guid}</guid>
      <pubDate>{pub_date}</pubDate>
      <dc:creator>{author}</dc:creator>
      <description>{post_description}</description>
      <content:encoded><![CDATA[{full_content}]]></content:encoded>
{thumbnail_xml}{categories_xml}    </item>"""
        )

    items_xml = "\n".join(items)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:content="http://purl.org/rss/1.0/modules/content/"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:atom="http://www.w3.org/2005/Atom"
  xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>{escape_xml(title)}</title>
    <link>{escape_xml(SITE_URL)}</link>
    <description>{escape_xml(description)}</description>
    <language>en</language>
    <lastBuildDate>{now}</lastBuildDate>
    <atom:link href="{escape_xml(feed_url)}" rel="self" type="application/rss+xml"/>
{items_xml}
  </channel>
</rss>"""


def build_index(base_url, category_feeds):
    cat_links = "\n".join(
        f'    <li><a href="{slug}.xml">{name}</a></li>'
        for slug, name in sorted(category_feeds, key=lambda x: x[1])
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>The Wire RSS Feed</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 600px; margin: 2rem auto; padding: 0 1rem; }}
    a {{ color: #b71c1c; }}
    code {{ background: #f5f5f5; padding: 2px 6px; border-radius: 3px; }}
  </style>
</head>
<body>
  <h1>The Wire RSS Feed</h1>
  <p>Main feed: <a href="feed.xml"><code>{base_url}/feed.xml</code></a></p>
  <h2>Category Feeds</h2>
  <ul>
{cat_links}
  </ul>
  <p>Add any of these URLs to your RSS reader.</p>
</body>
</html>"""


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # Copy static assets
    script_dir = os.path.dirname(__file__)
    placeholder_src = os.path.join(script_dir, "placeholder.png")
    if os.path.exists(placeholder_src):
        shutil.copy2(placeholder_src, os.path.join(OUT_DIR, "placeholder.png"))

    # Determine base URL from environment or default
    base_url = os.environ.get("BASE_URL", "").rstrip("/")

    # Generate main feed
    print("Fetching main feed...")
    posts = fetch_posts(30)
    feed_url = f"{base_url}/feed.xml" if base_url else "feed.xml"
    rss = build_rss(posts, feed_url, base_url=base_url)
    with open(os.path.join(OUT_DIR, "feed.xml"), "w", encoding="utf-8") as f:
        f.write(rss)
    print(f"  Wrote feed.xml ({len(posts)} posts)")

    # Fetch categories and generate per-category feeds
    print("Fetching categories...")
    categories = fetch_categories()
    # Filter to categories with a reasonable number of posts
    categories = [c for c in categories if c.get("count", 0) > 10]
    print(f"  Found {len(categories)} categories")

    category_feeds = []
    for cat in categories:
        slug = cat["slug"]
        name = html.unescape(cat["name"])
        cat_id = cat["id"]
        print(f"  Fetching category: {name} ({slug})...")
        try:
            cat_posts = fetch_posts(30, category_id=cat_id)
        except Exception as e:
            print(f"    Error fetching {slug}: {e}")
            continue
        cat_feed_url = f"{base_url}/{slug}.xml" if base_url else f"{slug}.xml"
        cat_rss = build_rss(
            cat_posts,
            cat_feed_url,
            base_url=base_url,
            title=f"The Wire - {name}",
            description=f"Latest articles from The Wire in the {name} category.",
        )
        with open(os.path.join(OUT_DIR, f"{slug}.xml"), "w", encoding="utf-8") as f:
            f.write(cat_rss)
        category_feeds.append((slug, name))
        print(f"    Wrote {slug}.xml ({len(cat_posts)} posts)")

    # Generate index page
    index_html = build_index(base_url, category_feeds)
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)
    print("Wrote index.html")
    print("Done!")


if __name__ == "__main__":
    main()
