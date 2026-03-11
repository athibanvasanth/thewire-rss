# indie-feeds

Custom RSS feed generator for Indian independent media sites that don't offer RSS feeds.

Feeds are auto-generated every 30 minutes via GitHub Actions and served through GitHub Pages.

## Feeds

| Feed | Source | URL |
|------|--------|-----|
| The Wire | All categories | [feed.xml](https://athibanvasanth.github.io/indie-feeds/feed.xml) |
| The Wire — Government | Government category | [government.xml](https://athibanvasanth.github.io/indie-feeds/government.xml) |
| The Wire — Politics | Politics category | [politics.xml](https://athibanvasanth.github.io/indie-feeds/politics.xml) |
| The Wire — Rights | Rights category | [rights.xml](https://athibanvasanth.github.io/indie-feeds/rights.xml) |
| Scroll Newsletter | Daily news briefing | [scroll.xml](https://athibanvasanth.github.io/indie-feeds/scroll.xml) |
| The Caravan | Politics and culture | [caravan.xml](https://athibanvasanth.github.io/indie-feeds/caravan.xml) |
| EPW | Social science journal | [epw.xml](https://athibanvasanth.github.io/indie-feeds/epw.xml) |

## How it works

Each site is scraped using a different strategy based on what's available:

- **The Wire** — WordPress REST API (`/wp-json/wp/v2/`)
- **Scroll Newsletter** — Pinia state extraction from page source
- **The Caravan** — JSON-LD structured data
- **EPW** — OpenGraph meta tags

Feeds are generated as RSS 2.0 with support for media thumbnails, full HTML content, author info, and categories.

## Usage

Copy any feed URL from the table above and add it to your RSS reader (Inoreader, Feedly, Newsblur, etc.).

## Self-hosting

```bash
pip install -r requirements.txt
export BASE_URL="http://localhost:8000/"
python generate_feed.py
python generate_scroll_feed.py
python generate_caravan_feed.py
python generate_epw_feed.py
# feeds are generated in the public/ directory
```
