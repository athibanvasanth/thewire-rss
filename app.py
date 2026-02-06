import datetime
import html
import re
import requests
from flask import Flask, Response

app = Flask(__name__)

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


def strip_html(text):
    return re.sub(r"<[^>]+>", "", text).strip()


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


def fetch_posts(count=30):
    params = {
        "per_page": count,
        "_embed": "author,wp:term",
        "orderby": "date",
        "order": "desc",
    }
    resp = SESSION.get(WP_API, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def build_rss(posts):
    now = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S +0000"
    )

    items = []
    for post in posts:
        title = escape_xml(html.unescape(post["title"]["rendered"]))
        link = escape_xml(post["link"])
        pub_date = format_rfc822(post["date"])
        description = escape_xml(
            strip_html(html.unescape(post["excerpt"]["rendered"]))
        )
        content = post["content"]["rendered"]
        guid = escape_xml(post["guid"]["rendered"])

        # Extract author name
        author = "The Wire"
        embedded = post.get("_embedded", {})
        authors = embedded.get("author", [])
        if authors and authors[0].get("name"):
            author = escape_xml(authors[0]["name"])

        # Extract categories
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
      <title>{title}</title>
      <link>{link}</link>
      <guid isPermaLink="false">{guid}</guid>
      <pubDate>{pub_date}</pubDate>
      <dc:creator>{author}</dc:creator>
      <description>{description}</description>
      <content:encoded><![CDATA[{content}]]></content:encoded>
{categories_xml}    </item>"""
        )

    items_xml = "\n".join(items)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:content="http://purl.org/rss/1.0/modules/content/"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{escape_xml(FEED_TITLE)}</title>
    <link>{escape_xml(SITE_URL)}</link>
    <description>{escape_xml(FEED_DESCRIPTION)}</description>
    <language>en</language>
    <lastBuildDate>{now}</lastBuildDate>
    <atom:link href="{escape_xml(SITE_URL)}/feed" rel="self" type="application/rss+xml"/>
{items_xml}
  </channel>
</rss>"""


@app.route("/")
def index():
    return (
        "<h1>The Wire RSS Feed</h1>"
        '<p><a href="/feed">RSS Feed</a></p>'
        "<p>Add <code>/feed</code> to your RSS reader.</p>"
    )


@app.route("/feed")
def feed():
    posts = fetch_posts(30)
    rss_xml = build_rss(posts)
    return Response(rss_xml, mimetype="application/rss+xml; charset=utf-8")


@app.route("/feed/<category>")
def category_feed(category):
    # First resolve category slug to ID
    cat_resp = SESSION.get(
        WP_CATEGORIES_API,
        params={"slug": category},
        timeout=10,
    )
    cat_resp.raise_for_status()
    cats = cat_resp.json()
    if not cats:
        return Response("Category not found", status=404)

    cat_id = cats[0]["id"]
    params = {
        "per_page": 30,
        "_embed": "author,wp:term",
        "orderby": "date",
        "order": "desc",
        "categories": cat_id,
    }
    resp = SESSION.get(WP_API, params=params, timeout=15)
    resp.raise_for_status()
    posts = resp.json()
    rss_xml = build_rss(posts)
    return Response(rss_xml, mimetype="application/rss+xml; charset=utf-8")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
