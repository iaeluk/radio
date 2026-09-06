#!/usr/bin/env python3
"""Builds the radio's pages from the MP3s in tracks/.

All you do is drop `Artist - Title.mp3` into tracks/ and push; this script
(run by the GitHub Actions workflow) does the rest:

  - scans tracks/ for MP3s,
  - reads artist + title out of each file name,
  - writes tracks/playlist.json,
  - writes one page per song (playlist/<slug>.html) so every song has its
    own address, plus playlist/index.html for the /playlist list page,
  - fills the shared regions in index.html and the generated pages,
  - writes sitemap.xml.

The slugs have to agree with assignSlugs()/slugify() in assets/js/app.js,
and the __ITEM__ payload has to match what seedRoute() expects. Keep the two
in step, or a link opens a page for a song the deck cannot find.

Usage:
  python3 tools/build.py          build everything
  python3 tools/build.py --check  exit 1 if a generated file is stale
"""

import argparse
import html
import json
import os
import re
import sys
import unicodedata
from urllib.parse import quote

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
TEMPLATE = os.path.join(TOOLS, "template.html")
TRACKS_DIR = os.path.join(ROOT, "tracks")
PLAYLIST_DIR = os.path.join(ROOT, "playlist")
MANIFEST = os.path.join(ROOT, "tracks", "playlist.json")
INDEX = os.path.join(ROOT, "index.html")
SITEMAP = os.path.join(ROOT, "sitemap.xml")

STATION = "radio"
STATION_NAME = "radio"
STATION_TAG = "playlist"
SITE_DESC = "A radio that plays itself, one song at a time."

# The URL under which the site is served, root included. Replace when you
# know the repo's name, or leave it and only sitemap.xml will be off.
BASE = "https://iaeluk.github.io/radio"


def slugify(value):
    """Port of slugify() in assets/js/app.js — must stay in step with it."""
    s = unicodedata.normalize("NFD", value or "")
    s = "".join(c for c in s if unicodedata.combining(c) == 0)
    s = s.lower()
    s = re.sub(r"['\u2019]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"^-+|-+$", "", s)
    return s


def assign_slugs(items):
    """Port of assignSlugs() in assets/js/app.js — same result for the same titles."""
    seen = {}
    for t in items:
        base = slugify(t.get("title")) or "track"
        slug = base
        if seen.get(slug):
            slug = base + "-" + slugify(t.get("artist"))
        n = 2
        while seen.get(slug):
            slug = base + "-" + str(n)
            n += 1
        seen[slug] = True
        t["slug"] = slug
        t["kind"] = "playlist"
        t["key"] = "playlist/" + slug


def parse_filename(name):
    base = name[:-4] if name.lower().endswith(".mp3") else name
    if "-" in base:
        artist, _, title = base.partition("-")
        return artist.strip(), title.strip()
    return STATION_NAME, base.strip()


def scan_tracks():
    tracks = []
    if not os.path.isdir(TRACKS_DIR):
        return tracks
    for name in sorted(os.listdir(TRACKS_DIR)):
        if not name.lower().endswith(".mp3"):
            continue
        artist, title = parse_filename(name)
        tracks.append({"title": title, "artist": artist, "file": name})
    return tracks


def manifest_payload(tracks):
    assign_slugs(tracks)
    return {"station": STATION, "name": STATION_NAME, "tracks": tracks}


def make_rows(tracks, root):
    rows = []
    for t in tracks:
        rows.append(
            '<li><a class="track" href="%splaylist/%s.html"><span class="tr-n">%s</span>'
            '<span class="tr-t"><span class="tr-line"><span class="tr-title">%s</span></span>'
            '<span class="tr-artist">%s</span></span>'
            '<span class="tr-s"><span class="tr-st"></span></span></a>'
            '<a class="tr-link" href="%splaylist/%s.html" title="Permalink &#8212; press to copy">#</a></li>'
            % (root, t["slug"], str(tracks.index(t) + 1).zfill(2),
               html.escape(t["title"]), html.escape(t["artist"]),
               root, t["slug"])
        )
    return "\n".join(rows)


def tabs_block(root):
    return (
        '<a class="seg-b is-on" id="tabSongs" href="%splaylist/" aria-current="page">songs</a>\n'
        '              <a class="seg-b" id="tabPodcast" href="%spodcast/">podcast</a>'
        % (root, root)
    )


def panel_block():
    return (
        '<span id="playlistKind">playlist</span> &#8212; <span id="playlistName">'
        + html.escape(STATION_NAME) + "</span>"
    )


def note_block(tracks):
    n = len(tracks)
    return "%d track%s, on repeat" % (n, "" if n == 1 else "s")


def replace_region(text, name, content):
    start = "<!-- page:%s -->" % name
    end = "<!-- /page:%s -->" % name
    s = text.find(start)
    e = text.find(end)
    if s < 0 or e < 0:
        raise RuntimeError("region not found: " + name)
    s += len(start)
    return text[:s] + "\n" + content + "\n" + text[e:]


def item_script(item):
    payload = json.dumps(item, ensure_ascii=False, sort_keys=True).replace("<", "\\u003c")
    return "<script>window.__ITEM__ = %s;</script>" % payload


def base_page(template, root, tracks, title, desc, canon, item=None, panel="playlist"):
    page = template
    page = replace_region(page, "head",
        "<title>%s</title>\n"
        '<meta name="description" content="%s">\n'
        '<link rel="canonical" href="%s">'
        % (html.escape(title), html.escape(desc), canon))
    page = replace_region(page, "data", item_script(item) if item else "")
    page = replace_region(page, "panel", panel_block())
    page = replace_region(page, "tabs", tabs_block(root))
    page = replace_region(page, "list", make_rows(tracks, root))
    page = replace_region(page, "note", note_block(tracks))
    page = page.replace("{{ROOT}}", root)
    page = page.replace("{{URL}}", BASE)
    return page


def write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def render():
    """Return {path: content} for every generated file, without touching disk."""
    tracks = scan_tracks()
    payload = manifest_payload(tracks)

    with open(TEMPLATE, "r", encoding="utf-8") as f:
        template = f.read()

    out = {}

    # Home: /
    out[INDEX] = base_page(
        template, "", tracks,
        STATION_NAME + " radio",
        SITE_DESC,
        BASE + "/")

    # The list: /playlist
    out[os.path.join(PLAYLIST_DIR, "index.html")] = base_page(
        template, "../", tracks,
        STATION_NAME + " radio &#8212; playlist",
        SITE_DESC,
        BASE + "/playlist")

    # One page per song: /playlist/<slug>
    out[MANIFEST] = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    for t in tracks:
        out[os.path.join(PLAYLIST_DIR, t["slug"] + ".html")] = base_page(
            template, "../", tracks,
            "%s \u2014 %s radio" % (t["title"], STATION_NAME),
            "%s by %s" % (t["title"], t["artist"]),
            BASE + "/playlist/" + t["slug"],
            item=t)

    for path, content in sitemap_pages(tracks).items():
        out[path] = content

    return out


def sitemap_pages(tracks):
    urls = [BASE + "/", BASE + "/playlist"]
    urls += [BASE + "/playlist/" + t["slug"] for t in tracks]
    body = "".join("  <url><loc>%s</loc></url>\n" % u for u in urls)
    return {SITEMAP:
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + body + "</urlset>\n"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    out = render()

    if args.check:
        stale = check(out)
        if stale:
            print("stale files:")
            for p in sorted(stale):
                print("  " + p)
            return 1
        print("OK")
        return 0

    os.makedirs(PLAYLIST_DIR, exist_ok=True)
    for path, content in out.items():
        write(path, content)

    # Drop pages for songs that no longer exist.
    slugs = {os.path.basename(p) for p in out if p.startswith(PLAYLIST_DIR + os.sep)}
    for name in list(os.listdir(PLAYLIST_DIR)):
        if name.endswith(".html") and name not in slugs:
            os.remove(os.path.join(PLAYLIST_DIR, name))

    print("built %d track(s)" % len(scan_tracks()))
    return 0


def check(out):
    import hashlib
    stale = []
    for path, content in sorted(out.items()):
        if not os.path.exists(path):
            stale.append(path)
            continue
        if hashlib.sha1(content.encode("utf-8")).hexdigest() != \
           hashlib.sha1(open(path, "rb").read()).hexdigest():
            stale.append(path)
    return stale


if __name__ == "__main__":
    sys.exit(main())