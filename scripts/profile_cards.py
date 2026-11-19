#!/usr/bin/env python3
"""Profile README cards for github.com/Makimum, drawn as plain SVG.

All of it is our own code: numbers come from the GitHub GraphQL API and the
ASCII portrait from the GitHub avatar. No third-party card service.

    GH_TOKEN=... python3 scripts/profile_cards.py live dist     # neofetch, stats, heatmap
    python3 scripts/profile_cards.py static assets              # banner + link buttons

The daily workflow runs the `live` command and publishes to the `output` branch.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

LOGIN = "Makimum"
PROMPT_USER = "maksim"

# ---- what the cards say (edit freely) -------------------------------------
ROLE = "founder · full-stack · web3"
LOCATION = "San Francisco"
BUILDING = [("VettaX", "posting autopilot for founders"),
            ("RookieAI", "UK uni admissions predictor")]
STACK = "TypeScript  Python  Postgres  Solidity"
PORTRAIT_CROP = (0.35, 0.27, 1.0, 0.92)  # face area of the avatar (left, top, right, bottom)
BANNER = "MAKIMUM"
TAGLINE = "founder · full-stack · shipping VettaX & RookieAI"
LINKS = [  # (file slug, tag, label) - the URLs live in README.md
    ("github", "gh", "@makimum"),
    ("web", "www", "vetta-x.com"),
    ("x", "x", "@makimum_dev"),
    ("linkedin", "in", "maxim-fursov"),
]

# ---- look -----------------------------------------------------------------
W = 860
FONT = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
P = dict(bg="#0a0d12", bar="#121821", tile="#0f141b", line="#232c38",
         text="#d5dde7", dim="#7b8796", faint="#566170",
         green="#4ade80", cyan="#38bdf8", amber="#fbbf24", rose="#fb7185", violet="#a78bfa")
HEAT = ["#19202a", "#0f4d2a", "#13803f", "#22b455", "#4ade80"]

CSS = f"""
text{{font-family:{FONT};fill:{P['text']};white-space:pre}}
.dim{{fill:{P['dim']}}}.faint{{fill:{P['faint']}}}.g{{fill:{P['green']}}}.c{{fill:{P['cyan']}}}
.a{{fill:{P['amber']}}}.r{{fill:{P['rose']}}}.v{{fill:{P['violet']}}}.b{{font-weight:700}}
@media (prefers-reduced-motion:no-preference){{
.in{{animation:in .5s ease-out both}}
.type{{animation:type .6s steps(16,end) both}}
.pop{{animation:pop .45s cubic-bezier(.2,.8,.2,1) both}}
.cur{{animation:in .2s both,blink 1.1s steps(1,end) infinite}}
@keyframes in{{from{{opacity:0;transform:translateY(5px)}}to{{opacity:1;transform:none}}}}
@keyframes type{{from{{clip-path:inset(0 100% 0 0)}}to{{clip-path:inset(0 0 0 0)}}}}
@keyframes pop{{from{{opacity:0;transform:translateY(-12px)}}to{{opacity:1;transform:none}}}}
@keyframes blink{{50%{{opacity:0}}}}
}}
"""


def esc(s) -> str:
    return escape(str(s), {'"': "&quot;"})


def delay(ms: float) -> str:
    return f' style="animation-delay:{ms:.0f}ms"'


def mono(x, y, segs, size=14, cls="", extra="", anchor=""):
    """One line of monospace text pinned to a fixed grid (0.6em per char), so
    every viewer's font lines up the same way. segs = [(text, css class)]."""
    if isinstance(segs, str):
        segs = [(segs, "")]
    plain = "".join(t for t, _ in segs)
    width = len(plain) * size * 0.6
    spans = "".join(f'<tspan class="{c}">{esc(t)}</tspan>' if c else esc(t) for t, c in segs)
    a = f' text-anchor="{anchor}"' if anchor else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" textLength="{width:.1f}" '
            f'lengthAdjust="spacingAndGlyphs" xml:space="preserve"{a} class="{cls}"{extra}>{spans}</text>')


def prompt(y, cmd, start=0, x=28, size=14):
    head = f"{PROMPT_USER}@github:~$ "
    hw = len(head) * size * 0.6
    return (mono(x, y, [(f"{PROMPT_USER}@github", "g"), (":", "dim"), ("~", "c"), ("$ ", "dim")],
                 size, "in", delay(start))
            + mono(x + hw, y, cmd, size, "type", delay(start + 150)))


def cursor(x, y, start, size=14):
    return (f'<rect x="{x:.1f}" y="{y - size * 0.8:.1f}" width="{size * 0.6:.1f}" height="{size:.1f}" '
            f'fill="{P["green"]}" class="cur"{delay(start)}/>')


def window(h, title, body, label):
    dots = "".join(f'<circle cx="{20 + i * 20}" cy="18" r="6" fill="{c}"/>'
                   for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840")))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" '
            f'role="img" aria-label="{esc(label)}"><title>{esc(label)}</title><style>{CSS}</style>'
            f'<defs><clipPath id="win"><rect width="{W}" height="{h}" rx="12"/></clipPath>'
            f'<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">'
            f'<rect width="4" height="1" fill="#fff" opacity=".018"/></pattern></defs>'
            f'<g clip-path="url(#win)"><rect width="{W}" height="{h}" fill="{P["bg"]}"/>'
            f'<rect width="{W}" height="36" fill="{P["bar"]}"/><rect y="36" width="{W}" height="1" fill="{P["line"]}"/>'
            f'<rect y="37" width="{W}" height="{h - 37}" fill="url(#scan)"/></g>'
            f'<rect x=".5" y=".5" width="{W - 1}" height="{h - 1}" rx="11.5" fill="none" stroke="{P["line"]}"/>'
            f'{dots}{mono(W / 2, 22.5, title, 12, "dim", anchor="middle")}{body}</svg>')


# ---- data -----------------------------------------------------------------
QUERY = """query($login:String!){user(login:$login){
  name createdAt avatarUrl(size:256) followers{totalCount}
  publicRepos: repositories(ownerAffiliations:OWNER, privacy:PUBLIC){totalCount}
  repos: repositories(ownerAffiliations:OWNER, privacy:PUBLIC, isFork:false, first:100){
    nodes{stargazerCount languages(first:10, orderBy:{field:SIZE, direction:DESC}){edges{size node{name color}}}}}
  contributionsCollection{totalCommitContributions totalPullRequestContributions
    contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""


def fetch(url, data=None, token=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "profile-cards"})
    if token:
        req.add_header("Authorization", f"bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def load():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("set GH_TOKEN")
    body = json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode()
    res = json.loads(fetch("https://api.github.com/graphql", body, token))
    if res.get("errors"):
        sys.exit(f"graphql: {res['errors']}")
    u = res["data"]["user"]
    cc = u["contributionsCollection"]
    days = [d for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    langs = {}
    for r in u["repos"]["nodes"]:
        for e in r["languages"]["edges"]:
            n = e["node"]
            langs.setdefault(n["name"], [0, n["color"] or P["dim"]])[0] += e["size"]
    total = sum(v[0] for v in langs.values()) or 1
    top = [kv for kv in sorted(langs.items(), key=lambda kv: -kv[1][0]) if kv[1][0] / total >= 0.001][:6]
    return dict(
        name=u["name"] or LOGIN,
        created=dt.datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00")),
        avatar=fetch(u["avatarUrl"]),
        followers=u["followers"]["totalCount"],
        repos=u["publicRepos"]["totalCount"],
        stars=sum(r["stargazerCount"] for r in u["repos"]["nodes"]),
        commits=cc["totalCommitContributions"],
        prs=cc["totalPullRequestContributions"],
        total=cc["contributionCalendar"]["totalContributions"],
        weeks=[[d["contributionCount"] for d in w["contributionDays"]] for w in cc["contributionCalendar"]["weeks"]],
        first_day=dt.date.fromisoformat(days[0]["date"]),
        counts=[d["contributionCount"] for d in days],
        langs=[(n, v[0] / total, v[1]) for n, v in top],
    )


def streaks(counts):
    cur, i = 0, len(counts) - 1
    if i >= 0 and counts[i] == 0:  # today isn't over yet
        i -= 1
    while i >= 0 and counts[i] > 0:
        cur, i = cur + 1, i - 1
    best = run = 0
    for c in counts:
        run = run + 1 if c else 0
        best = max(best, run)
    return cur, best


def uptime(created):
    now = dt.datetime.now(dt.timezone.utc)
    months = (now.year - created.year) * 12 + now.month - created.month
    y, m = divmod(max(months, 0), 12)
    return (f"{y}y " if y else "") + f"{m}m on GitHub"


# ---- cards ----------------------------------------------------------------
RAMP = " .,:;i1tfLCG08@"


def portrait(avatar: bytes, cols=46, cell_w=5.4, cell_h=9.8):
    """Colour ASCII of the avatar, faded to a circle."""
    from PIL import Image, ImageEnhance, ImageOps
    im = Image.open(io.BytesIO(avatar)).convert("RGB")
    w, h = im.size
    l, t, r, b = PORTRAIT_CROP
    im = ImageOps.fit(im.crop((int(l * w), int(t * h), int(r * w), int(b * h))), (256, 256))
    im = ImageEnhance.Contrast(ImageOps.autocontrast(im, cutoff=1)).enhance(1.15)
    rows = round(cols * cell_w / cell_h)
    small = im.resize((cols, rows), Image.LANCZOS)
    lum = ImageOps.grayscale(small)
    lines = []
    for r in range(rows):
        segs, prev = [], None
        for c in range(cols):
            dx, dy = (c + .5) / cols - .5, (r + .5) / rows - .5
            edge = max(0.0, min(1.0, (0.5 - (dx * dx + dy * dy) ** .5) / 0.06))
            v = lum.getpixel((c, r)) / 255 * edge
            ch = RAMP[min(len(RAMP) - 1, int(v * len(RAMP)))]
            rgb = small.getpixel((c, r))
            lift = [min(255, int(40 + k * 0.9)) for k in rgb]  # keep dark pixels readable on black
            col = "#%02x%02x%02x" % tuple((k // 24) * 24 for k in lift)
            if segs and col == prev:
                segs[-1][0] += ch
            else:
                segs.append([ch, col])
            prev = col
        lines.append(segs)
    return lines, rows


def neofetch(d):
    top, px, cw, chh = 84, 28, 5.4, 9.8
    lines, rows = portrait(d["avatar"], cell_w=cw, cell_h=chh)
    body = [prompt(64, "neofetch", 0)]
    for r, segs in enumerate(lines):
        plain = "".join(s[0] for s in segs)
        spans = "".join(f'<tspan fill="{c}">{esc(t)}</tspan>' for t, c in segs)
        body.append(f'<text x="{px}" y="{top + (r + 1) * chh:.1f}" font-size="9" textLength="{len(plain) * cw:.1f}" '
                    f'lengthAdjust="spacingAndGlyphs" xml:space="preserve" class="in"{delay(500 + r * 22)}>{spans}</text>')
    rx, ry, step = 300, 104, 20.5
    head = f"{PROMPT_USER}@github"
    info = [
        ("Name", d["name"]),
        ("Role", ROLE),
        ("Location", LOCATION),
        ("Building", f"{BUILDING[0][0]:<9}{BUILDING[0][1]}"),
        ("", f"{BUILDING[1][0]:<9}{BUILDING[1][1]}"),
        ("Stack", STACK),
        ("Repos", f"{d['repos']} public · {d['stars']} stars"),
        ("Followers", str(d["followers"])),
        ("Contribs", f"{d['total']} in the last year"),
        ("Uptime", uptime(d["created"])),
    ]
    body.append(mono(rx, ry - 8, [(PROMPT_USER, "g b"), ("@", "dim"), ("github", "c b")], 15, "in", delay(650)))
    body.append(mono(rx, ry + 10, "─" * len(head), 15, "faint in", delay(650)))
    for i, (k, v) in enumerate(info):
        body.append(mono(rx, ry + 32 + i * step, [(f"{k:<10}", "c"), (v, "")], 13.5, "in", delay(720 + i * 65)))
    sy = ry + 32 + len(info) * step - 6
    for i, c in enumerate([P["faint"], P["rose"], P["green"], P["amber"], P["cyan"], P["violet"], P["dim"], P["text"]]):
        body.append(f'<rect x="{rx + i * 26}" y="{sy}" width="22" height="12" rx="2" fill="{c}" class="in"{delay(1500 + i * 40)}/>')
    py = max(top + rows * chh, sy + 12) + 34
    head_w = (len(head) + 3) * 14 * 0.6
    body.append(mono(28, py, [(f"{PROMPT_USER}@github", "g"), (":", "dim"), ("~", "c"), ("$ ", "dim")], 14, "in", delay(1800)))
    body.append(cursor(28 + head_w, py, 1850))
    return window(py + 22, f"{PROMPT_USER}@github: ~ — zsh", "".join(body),
                  f"{d['name']} — {ROLE}. Building {', '.join(b[0] for b in BUILDING)}.")


GLYPHS = {
    "M": ["X...X", "XX.XX", "X.X.X", "X.X.X", "X...X", "X...X", "X...X"],
    "A": [".XXX.", "X...X", "X...X", "XXXXX", "X...X", "X...X", "X...X"],
    "K": ["X...X", "X..X.", "X.X..", "XX...", "X.X..", "X..X.", "X...X"],
    "I": ["XXXXX", "..X..", "..X..", "..X..", "..X..", "..X..", "XXXXX"],
    "U": ["X...X", "X...X", "X...X", "X...X", "X...X", "X...X", ".XXX."],
}


def banner():
    cell, size, depth = 15, 13, 3
    cols = len(BANNER) * 6 - 1
    left, top = (W - cols * cell) / 2, 92
    px = []
    for li, ch in enumerate(BANNER):
        for r, row in enumerate(GLYPHS[ch]):
            for c, on in enumerate(row):
                if on == "X":
                    col = li * 6 + c
                    px.append(f'<rect x="{left + col * cell:.0f}" y="{top + r * cell}" width="{size}" height="{size}" rx="2" '
                              f'class="pop"{delay(250 + col * 22 + r * 8)}/>')
    word = "".join(px)
    shades = ["#0b3b20", "#0f5a2e", "#14743a"]
    layers = "".join(f'<g fill="{shades[i]}" transform="translate({(depth - i) * 2},{(depth - i) * 2})">{word}</g>'
                     for i in range(depth))
    body = (prompt(64, f"./banner.sh {BANNER.lower()}", 0)
            + f'<defs><linearGradient id="face" x1="{left}" x2="{left + cols * cell}" y1="0" y2="0" gradientUnits="userSpaceOnUse">'
            f'<stop offset="0" stop-color="{P["green"]}"/><stop offset="1" stop-color="{P["cyan"]}"/></linearGradient></defs>'
            + layers + f'<g fill="url(#face)">{word}</g>'
            + mono(W / 2, top + 7 * cell + 42, f"> {TAGLINE}", 13, "dim in", delay(1300), anchor="middle"))
    return window(top + 7 * cell + 66, "~/banner — ./banner.sh", body, f"{BANNER} banner")


def stats(d):
    tiles = [("contributions", d["total"], "last 12 months", "g"),
             ("commits", d["commits"], "last 12 months", "c"),
             ("pull requests", d["prs"], "last 12 months", "v"),
             ("stars", d["stars"], f"across {d['repos']} repos", "a"),
             ("followers", d["followers"], "on GitHub", "r")]
    gap, x0, y0 = 12, 28, 88
    tw = (W - 2 * x0 - gap * (len(tiles) - 1)) / len(tiles)
    body = [prompt(64, f"gh stats --user {LOGIN.lower()}", 0)]
    for i, (label, n, sub, cls) in enumerate(tiles):
        tx = x0 + i * (tw + gap)
        body.append(f'<g class="in"{delay(350 + i * 80)}><rect x="{tx:.1f}" y="{y0}" width="{tw:.1f}" height="88" rx="8" '
                    f'fill="{P["tile"]}" stroke="{P["line"]}"/>'
                    + mono(tx + 14, y0 + 24, label.upper(), 10.5, "dim")
                    + mono(tx + 14, y0 + 56, f"{n:,}", 26, f"{cls} b")
                    + mono(tx + 14, y0 + 76, sub, 10.5, "faint") + "</g>")
    ly = y0 + 88 + 36
    body.append(mono(x0, ly, [("top languages", "dim"), ("  by bytes in public repos", "faint")], 12, "in", delay(800)))
    bx, bw = x0, W - 2 * x0
    segs, cx = [], bx
    for i, (name, frac, color) in enumerate(d["langs"]):
        w = bw * frac / sum(f for _, f, _ in d["langs"])
        segs.append(f'<rect x="{cx:.1f}" y="{ly + 12}" width="{max(w - 2, 1):.1f}" height="10" fill="{color}"/>')
        cx += w
    body.append(f'<defs><clipPath id="bar"><rect x="{bx}" y="{ly + 12}" width="{bw}" height="10" rx="5"/></clipPath></defs>'
                f'<g clip-path="url(#bar)" class="in"{delay(850)}>{"".join(segs)}</g>')
    for i, (name, frac, color) in enumerate(d["langs"]):
        lx, lyy = x0 + (i % 3) * 270, ly + 46 + (i // 3) * 22
        body.append(f'<g class="in"{delay(950 + i * 60)}><circle cx="{lx + 5}" cy="{lyy - 4}" r="5" fill="{color}"/>'
                    + mono(lx + 16, lyy, [(f"{name:<12}", ""), (f"{frac * 100:5.1f}%", "dim")], 12.5) + "</g>")
    h = ly + 46 + ((len(d["langs"]) - 1) // 3) * 22 + 26
    return window(h, "~/stats — gh api graphql", "".join(body),
                  f"GitHub stats: {d['total']} contributions, {d['stars']} stars, {d['followers']} followers")


def heatmap(d):
    weeks = d["weeks"]
    nonzero = sorted(c for w in weeks for c in w if c)
    cuts = [nonzero[int(len(nonzero) * q)] for q in (.25, .5, .75)] if nonzero else [1, 2, 3]

    def level(c):
        return 0 if c == 0 else 1 + sum(c > k for k in cuts)

    cell, gap = 11, 3
    step = cell + gap
    gx = (W - (len(weeks) * step - gap) - 30) / 2 + 30
    gy = 140
    _, best = streaks(d["counts"])
    active = sum(1 for c in d["counts"] if c)
    body = [prompt(64, 'git log --since="1 year ago" | heatmap', 0),
            mono(28, 104, [(f"{d['total']:,}", "g b"), (" contributions in the last year", "")], 15, "in", delay(450)),
            mono(W - 28, 104, [("active days ", "dim"), (str(active), "c"), ("  best streak ", "dim"),
                               (f"{best}d", "c")], 12.5, "in", delay(500), anchor="end")]
    last_month = None
    for wi, _ in enumerate(weeks):
        day = d["first_day"] + dt.timedelta(days=wi * 7 - (d["first_day"].weekday() + 1) % 7)
        if day.month != last_month and wi < len(weeks) - 2:
            if last_month is not None or day.day <= 7:
                body.append(mono(gx + wi * step, gy - 8, day.strftime("%b"), 10, "dim in", delay(500)))
            last_month = day.month
    for r, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        body.append(mono(gx - 30, gy + r * step + 9, name, 10, "faint in", delay(500)))
    cells = []
    for wi, w in enumerate(weeks):
        offset = (7 - len(w)) if wi == 0 else 0
        for di, c in enumerate(w):
            cells.append(f'<rect x="{gx + wi * step:.1f}" y="{gy + (di + offset) * step}" width="{cell}" height="{cell}" rx="2" '
                         f'fill="{HEAT[level(c)]}" class="in"{delay(550 + wi * 14)}/>')
    body.append("".join(cells))
    ly = gy + 7 * step + 22
    body.append(mono(W - 28 - 5 * step - 44, ly, "less", 10, "faint in", delay(1300), anchor="end"))
    for i, col in enumerate(HEAT):
        body.append(f'<rect x="{W - 28 - 40 - (5 - i) * step:.1f}" y="{ly - 9}" width="{cell}" height="{cell}" rx="2" '
                    f'fill="{col}" class="in"{delay(1300)}/>')
    body.append(mono(W - 28, ly, "more", 10, "faint in", delay(1300), anchor="end"))
    return window(ly + 22, "~/activity — git log", "".join(body), f"{d['total']} contributions in the last year")


def link_button(tag, label):
    size = 12.5
    tw = max(len(tag), 2) * size * 0.6 + 14
    w = 12 + tw + 10 + len(label) * size * 0.6 + 16
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="34" viewBox="0 0 {w:.0f} 34" role="img" '
            f'aria-label="{esc(label)}"><style>{CSS}</style>'
            f'<rect x=".5" y=".5" width="{w - 1:.0f}" height="33" rx="8" fill="{P["bg"]}" stroke="{P["line"]}"/>'
            f'<rect x="7" y="7" width="{tw:.1f}" height="20" rx="5" fill="#10291b"/>'
            + mono(7 + tw / 2, 21.5, tag, size, "g b", anchor="middle")
            + mono(7 + tw + 10, 21.5, label, size) + "</svg>")


def write(path, svg):
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {path} ({len(svg) / 1024:.1f} KB)")


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("live", "static"):
        sys.exit(__doc__)
    cmd, out = sys.argv[1:]
    os.makedirs(out, exist_ok=True)
    if cmd == "static":
        write(f"{out}/banner.svg", banner())
        for slug, tag, label in LINKS:
            write(f"{out}/link-{slug}.svg", link_button(tag, label))
        return
    d = load()
    write(f"{out}/card-neofetch.svg", neofetch(d))
    write(f"{out}/card-stats.svg", stats(d))
    write(f"{out}/card-heatmap.svg", heatmap(d))


if __name__ == "__main__":
    main()
