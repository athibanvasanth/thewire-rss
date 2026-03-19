# indie-feeds

Custom RSS feed generators for independent media sites that don't offer RSS, plus a curated directory of non-mainstream feeds from India and around the world. Auto-generated every 30 minutes via GitHub Actions and served through GitHub Pages.

**Live site:** [athibanvasanth.github.io/indie-feeds](https://athibanvasanth.github.io/indie-feeds/)

## Generated Feeds

| Site | Strategy | Feed |
|------|----------|------|
| The Wire | WordPress REST API (`/wp-json/wp/v2/`) | [feed.xml](https://athibanvasanth.github.io/indie-feeds/feed.xml) |
| Scroll Newsletter | Pinia state extraction from page source | [scroll.xml](https://athibanvasanth.github.io/indie-feeds/scroll.xml) |
| The Caravan | JSON-LD structured data | [caravan.xml](https://athibanvasanth.github.io/indie-feeds/caravan.xml) |
| EPW | OpenGraph meta tags | [epw.xml](https://athibanvasanth.github.io/indie-feeds/epw.xml) |

The Wire also generates ~50 per-category feeds (politics, rights, economy, etc.) — see the [live site](https://athibanvasanth.github.io/indie-feeds/) for the full list.

## Curated RSS Directory

The index page also includes a curated directory of native RSS feeds from non-mainstream independent media (Al Jazeera, Democracy Now!, The Intercept, Jacobin, Glenn Greenwald, Chris Hedges, and more) with one-click copy-to-clipboard.

## How It Works

Each generator script targets a different site using whatever structured data is available:

- `generate_feed.py` — The Wire (WordPress API, fetches categories dynamically)
- `generate_scroll_feed.py` — Scroll Newsletter (Pinia/Stck.me state extraction)
- `generate_caravan_feed.py` — The Caravan (JSON-LD structured data)
- `generate_epw_feed.py` — EPW (OpenGraph meta tags)

All feeds are RSS 2.0 with media thumbnails, full HTML content, author info, and categories.

## Setup

```bash
pip install -r requirements.txt

export BASE_URL="https://athibanvasanth.github.io/indie-feeds"
python generate_feed.py
python generate_scroll_feed.py
python generate_caravan_feed.py
python generate_epw_feed.py

# feeds are generated in the public/ directory
```

## Deployment

GitHub Actions runs all generators every 30 minutes and deploys to GitHub Pages via `actions/deploy-pages`.
