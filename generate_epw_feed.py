import datetime
import os
import re

import requests

EPW_URL = "https://www.epw.in"
SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
)
OUT_DIR = os.path.join(os.path.dirname(__file__), "public")


def escape_xml(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def fetch_article_urls():
    resp = SESSION.get(EPW_URL, timeout=30)
    resp.raise_for_status()
    # Match journal article links like /journal/2026/9/editorials/...
    pattern = r'<a[^>]*href="(/journal/\d{4}/[^"]+\.html)"[^>]*>(.*?)</a>'
    matches = re.findall(pattern, resp.text, re.DOTALL)
    seen = set()
    urls = []
    for url, content in matches:
        if url in seen or "/ew-archive" in url:
            continue
        title = re.sub(r"<[^>]+>", "", content).strip()
        if not title or len(title) < 5:
            continue
        seen.add(url)
        urls.append(url)
    return urls


def extract_meta(html, prop):
    # Try property= first, then name=
    patterns = [
        rf'<meta[^>]*property="{prop}"[^>]*content="([^"]*)"',
        rf'<meta[^>]*content="([^"]*)"[^>]*property="{prop}"',
        rf'<meta[^>]*name="{prop}"[^>]*content="([^"]*)"',
        rf'<meta[^>]*content="([^"]*)"[^>]*name="{prop}"',
    ]
    for p in patterns:
        m = re.search(p, html)
        if m:
            return m.group(1)
    return ""


def fetch_article_meta(path):
    url = f"{EPW_URL}{path}"
    try:
        resp = SESSION.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"    Error fetching {path}: {e}")
        return None

    page = resp.text
    title = extract_meta(page, "og:title")
    if not title:
        return None

    description = extract_meta(page, "description")
    pub_date = extract_meta(page, "article:published_time")
    image = extract_meta(page, "og:image")
    if image and image.startswith("//"):
        image = "https:" + image

    # Extract author from citation_author or page content
    author = extract_meta(page, "citation_author")
    if not author:
        # Try to find author in the page body
        author_match = re.search(r'class="[^"]*author[^"]*"[^>]*>([^<]+)', page)
        if author_match:
            author = author_match.group(1).strip()
    if not author:
        author = "EPW"

    # Extract category from URL: /journal/YYYY/N/category/slug.html
    category = ""
    parts = path.strip("/").split("/")
    if len(parts) >= 4:
        category = parts[3].replace("-", " ").title()

    return {
        "title": title.strip(),
        "url": url,
        "description": description.strip(),
        "author": author.strip(),
        "date": pub_date,
        "image": image,
        "category": category,
    }


def format_rfc822(iso_str):
    if not iso_str:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(iso_str)
        return dt.strftime("%a, %d %b %Y %H:%M:%S %z")
    except (ValueError, AttributeError):
        return ""


def build_rss(articles, feed_url):
    now = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S +0000"
    )

    items = []
    for a in articles:
        title = escape_xml(a["title"])
        link = escape_xml(a["url"])
        desc = escape_xml(a["description"][:500]) if a["description"] else ""
        author = escape_xml(a["author"])
        pub_date = format_rfc822(a["date"])
        guid = link

        thumbnail_xml = ""
        if a.get("image"):
            img = escape_xml(a["image"])
            thumbnail_xml = (
                f'      <media:content url="{img}" medium="image" type="image/jpeg"/>\n'
                f'      <media:thumbnail url="{img}"/>\n'
                f'      <enclosure url="{img}" type="image/jpeg" length="0"/>\n'
            )

        category_xml = ""
        if a.get("category"):
            category_xml = f"      <category>{escape_xml(a['category'])}</category>\n"

        items.append(
            f"""    <item>
      <title>{title}</title>
      <link>{link}</link>
      <guid isPermaLink="true">{guid}</guid>
      <pubDate>{pub_date}</pubDate>
      <dc:creator>{author}</dc:creator>
      <description>{desc}</description>
{thumbnail_xml}{category_xml}    </item>"""
        )

    items_xml = "\n".join(items)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:content="http://purl.org/rss/1.0/modules/content/"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:atom="http://www.w3.org/2005/Atom"
  xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>Economic and Political Weekly</title>
    <link>{escape_xml(EPW_URL)}</link>
    <description>Economic and Political Weekly - India&apos;s premier social science journal since 1949</description>
    <language>en</language>
    <lastBuildDate>{now}</lastBuildDate>
    <atom:link href="{escape_xml(feed_url)}" rel="self" type="application/rss+xml"/>
{items_xml}
  </channel>
</rss>"""


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    base_url = os.environ.get("BASE_URL", "").rstrip("/")

    print("Fetching EPW homepage...")
    try:
        urls = fetch_article_urls()
    except Exception as e:
        print(f"  Failed to fetch EPW homepage: {e}")
        print("  Skipping EPW feed generation")
        return
    print(f"  Found {len(urls)} article URLs")

    articles = []
    for path in urls:
        print(f"  Fetching metadata: {path}")
        meta = fetch_article_meta(path)
        if meta:
            articles.append(meta)

    # Sort by date descending
    articles.sort(key=lambda a: a.get("date", ""), reverse=True)

    feed_url = f"{base_url}/epw.xml" if base_url else "epw.xml"
    rss = build_rss(articles, feed_url)
    with open(os.path.join(OUT_DIR, "epw.xml"), "w", encoding="utf-8") as f:
        f.write(rss)
    print(f"Wrote epw.xml ({len(articles)} articles)")


if __name__ == "__main__":
    main()
