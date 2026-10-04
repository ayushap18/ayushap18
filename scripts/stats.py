"""Builds assets/stats.svg from live GitHub data. Run by .github/workflows/stats.yml."""
import json, os, urllib.request, datetime, xml.etree.ElementTree as ET
from html import escape

LOGIN = "ayushap18"
SKIP_LANGS = {"HTML", "CSS", "Jupyter Notebook", "Makefile", "Dockerfile", "Shell", "SCSS"}
ACC, INK, MUTED, BG = "#C6FF3D", "#F4F4F0", "#8A8A86", "#0B0B0C"
SHADES = [ACC, "#8FBF2A", "#F4F4F0", "#B8B8B2", "#6E6E6A", "#3E3E3B"]
LEVELS = {"NONE": .06, "FIRST_QUARTILE": .3, "SECOND_QUARTILE": .5, "THIRD_QUARTILE": .75, "FOURTH_QUARTILE": 1}

QUERY = """query($login:String!){user(login:$login){
  repositories(ownerAffiliations:OWNER,isFork:false,privacy:PUBLIC,first:100){totalCount nodes{
    stargazerCount languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}}}
  contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}}}"""


def fetch():
    req = urllib.request.Request("https://api.github.com/graphql",
                                 json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
                                 {"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}"})
    data = json.load(urllib.request.urlopen(req))
    if "errors" in data:
        raise SystemExit(data["errors"])
    return data["data"]["user"]


def longest_streak(days):
    best = n = 0
    for d in days:
        n = n + 1 if d["contributionCount"] else 0
        best = max(best, n)
    return best


assert longest_streak([{"contributionCount": c} for c in [1, 2, 0, 3, 1, 4, 0]]) == 3


def render(u):
    repos = u["repositories"]
    cal = u["contributionsCollection"]["contributionCalendar"]
    weeks = cal["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    stars = sum(r["stargazerCount"] for r in repos["nodes"])

    langs = {}
    for r in repos["nodes"]:
        for e in r["languages"]["edges"]:
            if e["node"]["name"] not in SKIP_LANGS:
                langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:6]
    total = sum(v for _, v in top) or 1

    s = []
    # stat blocks
    for i, (val, label) in enumerate([(cal["totalContributions"], "CONTRIBUTIONS"), (longest_streak(days), "LONGEST STREAK"),
                                      (repos["totalCount"], "PUBLIC REPOS"), (stars, "STARS EARNED")]):
        x, y = 40 + (i % 2) * 170, 132 + (i // 2) * 80
        s.append(f'<text x="{x}" y="{y}" class="sans" font-size="44" font-weight="700" letter-spacing="-.03em" fill="{INK}">{val:,}</text>'
                 f'<text x="{x}" y="{y + 24}" class="mono label">{label}</text>')

    # heatmap
    cell, gap = 11, 3
    x0 = 1160 - len(weeks) * (cell + gap) + gap
    last_month = None
    for wi, w in enumerate(weeks):
        x = x0 + wi * (cell + gap)
        month = w["contributionDays"][0]["date"][5:7]
        if month != last_month and wi < len(weeks) - 2:
            name = datetime.date(2000, int(month), 1).strftime("%b")
            s.append(f'<text x="{x}" y="88" class="mono" font-size="11" fill="{MUTED}">{name}</text>')
            last_month = month
        for d in w["contributionDays"]:
            wd = datetime.date.fromisoformat(d["date"]).isoweekday() % 7
            fill = "#fff" if d["contributionLevel"] == "NONE" else ACC
            s.append(f'<rect x="{x}" y="{100 + wd * (cell + gap)}" width="{cell}" height="{cell}" rx="2.5" fill="{fill}" fill-opacity="{LEVELS[d["contributionLevel"]]}"/>')
    lx = 1160 - 5 * (cell + gap) - 40
    s.append(f'<text x="{lx - 8}" y="{216}" text-anchor="end" class="mono" font-size="11" fill="{MUTED}">less</text>')
    for i, op in enumerate(LEVELS.values()):
        s.append(f'<rect x="{lx + i * (cell + gap)}" y="207" width="{cell}" height="{cell}" rx="2.5" fill="{"#fff" if i == 0 else ACC}" fill-opacity="{op}"/>')
    s.append(f'<text x="1160" y="216" text-anchor="end" class="mono" font-size="11" fill="{MUTED}">more</text>')

    # language bar + legend
    s.append(f'<text x="40" y="288" class="mono label">TOP LANGUAGES</text>')
    s.append('<clipPath id="bar"><rect x="40" y="302" width="1120" height="10" rx="5"/></clipPath><g clip-path="url(#bar)">')
    x = 40.0
    for i, (name, v) in enumerate(top):
        w = 1120 * v / total
        s.append(f'<rect x="{x:.1f}" y="302" width="{w + 1:.1f}" height="10" fill="{SHADES[i]}"/>')
        x += w
    s.append("</g>")
    x = 40
    for i, (name, v) in enumerate(top):
        pct = f"{100 * v / total:.0f}%"
        s.append(f'<circle cx="{x + 5}" cy="342" r="5" fill="{SHADES[i]}"/>'
                 f'<text x="{x + 18}" y="347" class="mono" font-size="13" fill="#C9C9C4">{escape(name)} <tspan fill="{MUTED}">{pct}</tspan></text>')
        x += (len(name) + len(pct) + 1) * 8.5 + 48

    today = datetime.date.today().isoformat()
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="380" viewBox="0 0 1200 380" role="img" aria-label="{cal['totalContributions']} contributions in the last year, {stars} stars across {repos['totalCount']} public repos">
<defs>
  <pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="#fff" fill-opacity=".06"/></pattern>
  <clipPath id="card"><rect width="1200" height="380" rx="20"/></clipPath>
</defs>
<style>
  .mono{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}
  .sans{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Helvetica,Arial,sans-serif}}
  .label{{font-size:12px;letter-spacing:.16em;fill:{MUTED}}}
</style>
<g clip-path="url(#card)"><rect width="1200" height="380" fill="{BG}"/><rect width="1200" height="380" fill="url(#dots)"/></g>
<rect x=".5" y=".5" width="1199" height="379" rx="19.5" fill="none" stroke="#fff" stroke-opacity=".09"/>
<text x="40" y="52" class="mono label">ACTIVITY  /  LAST 12 MONTHS</text>
<text x="1160" y="52" text-anchor="end" class="mono label">UPDATED {today}</text>
<line x1="40" y1="256" x2="1160" y2="256" stroke="#fff" stroke-opacity=".08"/>
{"".join(s)}
</svg>
"""


if __name__ == "__main__":
    svg = render(fetch())
    ET.fromstring(svg)  # refuse to write a broken SVG
    path = os.path.join(os.path.dirname(__file__), "..", "assets", "stats.svg")
    open(path, "w").write(svg)
    print("wrote", os.path.normpath(path))
