import datetime
import json
import os
import re

import requests

SCROLL_URL = "https://scroll-newsletter.stck.me/"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "ScrollRSS/1.0"})
OUT_DIR = os.path.join(os.path.dirname(__file__), "public")


def escape_xml(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def fetch_posts():
    resp = SESSION.get(SCROLL_URL, timeout=30)
    resp.raise_for_status()
    match = re.search(
        r"window\.__INITIAL_PINIA_STATE__\s*=\s*(.+?);\s*</script>",
        resp.text,
        re.DOTALL,
    )
    if not match:
        raise Exception("Could not find Pinia state in Scroll page")
    state = json.loads(match.group(1))
    return state["siteContent"]["mixedPosts"]["content"]


def build_rss(posts, feed_url, base_url=""):
    now = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S +0000"
    )

    items = []
    for post in posts:
        title = escape_xml(post.get("title", "Untitled"))
        link = escape_xml(
            post.get("permalink", f"{SCROLL_URL}post/{post.get('id', '')}")
        )
        summary = escape_xml(post.get("summary", ""))

        pub_date = ""
        published = post.get("published", "")
        if published:
            try:
                dt = datetime.datetime.fromisoformat(published)
                pub_date = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
            except (ValueError, AttributeError):
                pass

        author = "Scroll"
        author_data = post.get("author", {})
        if isinstance(author_data, dict) and author_data.get("name"):
            author = escape_xml(author_data["name"])

        thumbnail_xml = ""
        cover_src = post.get("meta", {}).get("cover", {}).get("src", {})
        img_url = cover_src.get("image", "")
        if img_url:
            escaped_img = escape_xml(img_url)
            thumbnail_xml = (
                f'      <media:content url="{escaped_img}" medium="image" type="image/jpeg"/>\n'
                f'      <media:thumbnail url="{escaped_img}"/>\n'
                f'      <enclosure url="{escaped_img}" type="image/jpeg" length="0"/>\n'
            )

        items.append(
            f"""    <item>
      <title>{title}</title>
      <link>{link}</link>
      <guid isPermaLink="true">{link}</guid>
      <pubDate>{pub_date}</pubDate>
      <dc:creator>{author}</dc:creator>
      <description>{summary}</description>
{thumbnail_xml}    </item>"""
        )

    items_xml = "\n".join(items)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:content="http://purl.org/rss/1.0/modules/content/"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:atom="http://www.w3.org/2005/Atom"
  xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>Scroll Newsletter</title>
    <link>{escape_xml(SCROLL_URL)}</link>
    <description>Daily news briefing from Scroll.in</description>
    <language>en</language>
    <lastBuildDate>{now}</lastBuildDate>
    <atom:link href="{escape_xml(feed_url)}" rel="self" type="application/rss+xml"/>
{items_xml}
  </channel>
</rss>"""


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    base_url = os.environ.get("BASE_URL", "").rstrip("/")

    print("Fetching Scroll newsletter...")
    posts = fetch_posts()
    feed_url = f"{base_url}/scroll.xml" if base_url else "scroll.xml"
    rss = build_rss(posts, feed_url, base_url=base_url)
    with open(os.path.join(OUT_DIR, "scroll.xml"), "w", encoding="utf-8") as f:
        f.write(rss)
    print(f"Wrote scroll.xml ({len(posts)} posts)")


if __name__ == "__main__":
    main()
