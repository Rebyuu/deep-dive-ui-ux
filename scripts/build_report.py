#!/usr/bin/env python3
"""Builds the deep-dive review page from a session directory.

  python build_report.py <session-dir> [--out <dir>] [--max-width 900] [--inline] [--lang de|en]

--lang sets the language of the page chrome (labels, buttons); content comes
from the session and critiques as written.

--inline embeds every screenshot as a data URI, so index.html is one
self-contained file (larger, but it opens anywhere and can be passed around).

Reads session.json, shots/*.png and critique/*.json (per-screen critiques
plus consistency.json / consistency.md). Writes <out>/index.html and
<out>/img/*.jpg. Each goal is rendered as a storyboard: every step shows the
screenshot it happened on with a numbered marker at the tap point.
"""
import argparse, base64, glob, html, json, os, re, shutil, subprocess

esc = lambda s: html.escape(str(s if s is not None else ""), quote=True)


def convert(src, dst, max_width):
    """PNG -> JPEG at a bounded width; uses sips (macOS) or Pillow, else copies."""
    try:
        r = subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "72", "-Z", str(max_width * 2),
                            src, "--out", dst], capture_output=True)
        if r.returncode == 0:
            return dst
    except FileNotFoundError:
        pass
    try:
        from PIL import Image
        im = Image.open(src).convert("RGB")
        im.thumbnail((max_width, max_width * 3))
        im.save(dst, "JPEG", quality=72)
        return dst
    except Exception:
        png = dst[:-4] + ".png"
        shutil.copyfile(src, png)
        return png


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session"); ap.add_argument("--out"); ap.add_argument("--max-width", type=int, default=900)
    ap.add_argument("--inline", action="store_true", help="embed screenshots in index.html")
    ap.add_argument("--lang", choices=["de", "en"], default="de", help="language of the page chrome")
    o = ap.parse_args()
    d = o.session
    out = o.out or os.path.join(d, "report")
    os.makedirs(os.path.join(out, "img"), exist_ok=True)
    s = json.load(open(os.path.join(d, "session.json")))
    W, H = s["width"], s["height"]

    # images
    img = {}
    for sc in s["screens"]:
        src = os.path.join(d, sc["file"])
        if os.path.exists(src):
            f = convert(src, os.path.join(out, "img", sc["id"] + ".jpg"), o.max_width)
            if o.inline:
                mime = "image/jpeg" if f.endswith(".jpg") else "image/png"
                img[sc["id"]] = f"data:{mime};base64," + base64.b64encode(open(f, "rb").read()).decode()
            else:
                img[sc["id"]] = "img/" + os.path.basename(f)

    # critiques
    crit, cons, cons_md = {}, {}, ""
    for f in sorted(glob.glob(os.path.join(d, "critique", "*.json"))):
        data = json.load(open(f))
        if os.path.basename(f) == "consistency.json":
            cons = data
        elif isinstance(data, list):
            for c in data:
                crit[c["id"]] = c
    if os.path.exists(os.path.join(d, "critique", "consistency.md")):
        cons_md = open(os.path.join(d, "critique", "consistency.md")).read()

    screen_ids = [x["id"] for x in s["screens"]]
    title_of = {x["id"]: (crit.get(x["id"], {}).get("title") or x.get("title") or x["id"]) for x in s["screens"]}

    # back-links: screen -> goal steps
    used_in = {}
    for g in s["goals"]:
        for st in g["steps"]:
            used_in.setdefault(st["screen"], []).append((g["id"], st["n"]))

    def link_ids(text):
        t = esc(text)
        return re.sub(r"\b(\d{2}[a-z]?-[a-z0-9-]+)\b",
                      lambda m: f'<a href="#s-{m.group(1)}">{m.group(1)}</a>' if m.group(1) in screen_ids else m.group(1), t)

    def sev(x):
        v = (x or "").lower()
        return f'<b class="sev {esc(v)}">{esc(x if v != "good" else "gut")}</b>'

    counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
    for c in crit.values():
        for i in c.get("issues", []):
            if i.get("severity") in counts:
                counts[i["severity"]] += 1
    for g in s["goals"]:
        for st in g["steps"]:
            f = st.get("finding")
            if f and f["severity"] in counts:
                counts[f["severity"]] += 1

    # ---- goals as storyboards --------------------------------------------
    rows, goals_html = [], []
    for g in s["goals"]:
        n_total = sum(1 for x in g["steps"] if x["counts"])
        ideal = g.get("ideal")
        rows.append(f'<tr><td><a href="#g-{esc(g["id"])}">{esc(g["id"])}</a></td><td>{esc(g["title"])}</td>'
                    f'<td class="num">{n_total}</td><td class="num">{esc(ideal) if ideal else "–"}</td><td>{esc(g.get("verdict",""))}</td></tr>')
        cards, running = [], 0
        for st in g["steps"]:
            if st["counts"]:
                running += 1
            mark = ""
            if "x" in st and "y" in st:
                l, t = 100 * st["x"] / W, 100 * st["y"] / H
                mark = f'<span class="mark {esc(st["action"])}" style="left:{l:.2f}%;top:{t:.2f}%">{st["n"]}</span>'
                if "x2" in st and "y2" in st:
                    l2, t2 = 100 * st["x2"] / W, 100 * st["y2"] / H
                    mark += (f'<svg class="arrow" viewBox="0 0 100 100" preserveAspectRatio="none"><line x1="{l:.2f}" y1="{t:.2f}" '
                             f'x2="{l2:.2f}" y2="{t2:.2f}" vector-effect="non-scaling-stroke"/></svg>'
                             f'<span class="mark end" style="left:{l2:.2f}%;top:{t2:.2f}%"></span>')
            f = st.get("finding")
            find = f'<p class="finding">{sev(f["severity"])} {link_ids(f["text"])}</p>' if f else ""
            note = f'<p class="stnote">{link_ids(st["note"])}</p>' if st.get("note") else ""
            counter = f'<span class="count">{running}</span>' if st["counts"] else '<span class="count off" title="zählt nicht">–</span>'
            src = img.get(st["screen"])
            pic = (f'<a class="frame" href="#s-{esc(st["screen"])}" style="aspect-ratio:{W}/{H}">'
                   f'<img loading="lazy" src="{esc(src)}" alt="{esc(title_of.get(st["screen"]))}">{mark}</a>') if src else ""
            cards.append(f'''<li class="step{" has-finding" if f else ""}" id="g-{esc(g["id"])}-{st["n"]}">
  {pic}
  <div class="cap"><div class="caphead">{counter}<span class="act">{esc(st["action"])}</span></div>
  <p class="lbl">{esc(st.get("label") or "")}</p>{note}{find}
  <p class="on">auf <a href="#s-{esc(st["screen"])}">{esc(st["screen"])}</a></p></div></li>''')
        goals_html.append(f'''<section class="goal" id="g-{esc(g["id"])}">
  <header><h3><span class="gid">{esc(g["id"])}</span>{esc(g["title"])}</h3>
  <p class="meta"><span class="pill">{n_total} Interaktionen</span>{f'<span class="pill">ideal {esc(ideal)}</span>' if ideal else ''}</p></header>
  {f'<p class="intent">{esc(g["intent"])}</p>' if g.get("intent") else ''}
  <ol class="board">{"".join(cards)}</ol>
  {f'<p class="verdict">{link_ids(g["verdict"])}</p>' if g.get("verdict") else ''}
  <label class="notelabel" for="n-g-{esc(g["id"])}">Deine Notizen zu diesem Ablauf</label>
  <textarea class="note" id="n-g-{esc(g["id"])}" data-key="goal-{esc(g["id"])}" data-title="{esc(g["id"])} {esc(g["title"])}" rows="3"></textarea>
</section>''')

    # ---- screens by cluster ------------------------------------------------
    HEUR = [("visibility", "Status"), ("match", "Sprache"), ("control", "Kontrolle"), ("consistency", "Konsistenz"),
            ("errorPrevention", "Fehler vermeiden"), ("recognition", "Erkennen"), ("flexibility", "Effizienz"),
            ("minimalism", "Reduktion"), ("errorRecovery", "Fehler beheben"), ("help", "Hilfe")]

    def screen_card(sid):
        c = crit.get(sid, {})
        issues = sorted(c.get("issues", []), key=lambda x: x.get("severity", "P9"))
        iss = "".join(f'<li>{sev(i.get("severity"))}<div><strong>{esc(i.get("issue"))}</strong><p>{esc(i.get("why"))}</p>'
                      f'<p class="fix">→ {esc(i.get("fix"))}</p></div></li>' for i in issues)
        stg = "".join(f"<li>{esc(x)}</li>" for x in c.get("strengths", []))
        h = c.get("heuristics") or {}
        heur = "".join(f'<span class="h h{int(h[k]) if isinstance(h.get(k),(int,float)) else "na"}" title="{esc(lbl)}">'
                       f'<i>{esc(h.get(k) if isinstance(h.get(k),(int,float)) else "–")}</i><em>{esc(lbl)}</em></span>' for k, lbl in HEUR) if h else ""
        uses = used_in.get(sid, [])
        used = ("<p class=\"used\">Verwendet in: " + ", ".join(f'<a href="#g-{esc(g)}-{n}">{esc(g)} · Schritt {n}</a>' for g, n in uses) + "</p>") if uses else ""
        pic = f'<a class="shot" href="{esc(img[sid]) if not o.inline else "#s-" + esc(sid)}"><img loading="lazy" src="{esc(img[sid])}" alt=""></a>' if sid in img else ""
        return f'''<article class="screen" id="s-{esc(sid)}">
  {pic}
  <div class="crit"><header><span class="sid">{esc(sid)}</span><h4>{esc(title_of[sid])}</h4></header>
  {used}
  {f'<p class="job">{esc(c.get("job"))}</p>' if c.get("job") else ''}
  <p>{esc(c.get("verdict") or "Keine Einzelkritik.")}</p>
  {f'<h5>Stärken</h5><ul class="strengths">{stg}</ul>' if stg else ''}
  {f'<h5>Befunde</h5><ul class="issues">{iss}</ul>' if iss else ''}
  {f'<div class="heur">{heur}</div>' if heur else ''}</div>
  <div class="mine"><label class="notelabel" for="n-{esc(sid)}">Deine Gedanken</label>
  <textarea class="note" id="n-{esc(sid)}" data-key="{esc(sid)}" data-title="{esc(sid)} · {esc(title_of[sid])}" rows="8"></textarea></div>
</article>'''

    clusters = s["clusters"] or [{"id": "", "name": "Screens", "about": ""}]
    cl_html, nav = [], []
    for cl in clusters:
        ids = [x["id"] for x in s["screens"] if (x.get("cluster") or "") == cl["id"] or (not s["clusters"])]
        if not ids:
            continue
        nav.append(f'<a href="#c-{esc(cl["id"])}">{esc(cl["id"])} {esc(cl["name"])} <small>{len(ids)}</small></a>')
        cl_html.append(f'<section class="cluster" id="c-{esc(cl["id"])}"><h2><span class="ck">{esc(cl["id"])}</span>{esc(cl["name"])}</h2>'
                       f'<p class="sub">{esc(cl.get("about",""))}</p>{"".join(screen_card(i) for i in ids)}</section>')
    orphans = [x["id"] for x in s["screens"] if s["clusters"] and (x.get("cluster") or "") not in {c["id"] for c in s["clusters"]}]
    if orphans:
        nav.append(f'<a href="#c-other">Weitere <small>{len(orphans)}</small></a>')
        cl_html.append(f'<section class="cluster" id="c-other"><h2>Weitere Screens</h2>{"".join(screen_card(i) for i in orphans)}</section>')

    # ---- consistency ---------------------------------------------------------
    def cons_html():
        if not cons:
            return '<p class="sub">Keine Konsistenzanalyse vorhanden.</p>'
        parts = []
        ti = "".join(f'<li>{sev(x.get("severity"))}<div><strong>{link_ids(x.get("issue"))}</strong><p>{link_ids(", ".join(x.get("screens", [])))}</p>'
                     f'<p class="fix">→ {link_ids(x.get("fix"))}</p></div></li>' for x in cons.get("top_inconsistencies", []))
        parts.append(f'<h3>Größte Inkonsistenzen</h3><ul class="issues">{ti}</ul>')
        rules = "".join(f'''<li><span class="rid">{esc(r.get("id"))}</span><div><strong>{link_ids(r.get("rule"))}</strong><p>{link_ids(r.get("rationale"))}</p>
          {f'<p class="viol">Heute: {link_ids("; ".join(r.get("current_violations", [])))}</p>' if r.get("current_violations") else ''}
          <textarea class="note small" id="n-r-{esc(r.get("id"))}" data-key="rule-{esc(r.get("id"))}" data-title="Regel {esc(r.get("id"))}" rows="2" aria-label="Notiz zu {esc(r.get("id"))}" placeholder="Einverstanden? Anpassen?"></textarea></div></li>''' for r in cons.get("rules", []))
        parts.append(f'<h3>Platzierungsregeln</h3><ul class="issues">{rules}</ul>')
        for m in cons.get("matrix", []):
            occ = "".join(f'<tr><td>{link_ids(x.get("screen"))}</td><td>{esc(x.get("context"))}</td><td>{esc(x.get("position"))}</td>'
                          f'<td>{esc(x.get("style"))}</td><td>{esc(x.get("confirmation"))}</td></tr>' for x in m.get("occurrences", []))
            parts.append(f'<details><summary><strong>{esc(m.get("action"))}</strong> – {esc(m.get("verdict"))}</summary><div class="tw"><table>'
                         f'<thead><tr><th>Screen</th><th>Kontext</th><th>Position</th><th>Stil</th><th>Bestätigung</th></tr></thead><tbody>{occ}</tbody></table></div></details>')
        return "".join(parts)

    caveats = "".join(f"<li>{esc(c)}</li>" for c in s.get("caveats", []))
    page = TEMPLATE.format(
        app=esc(s["app"]), date=esc(s.get("date", "")), device=esc(s["device"]), build=esc(s.get("build", "")),
        n_screens=len(s["screens"]), n_goals=len(s["goals"]), p0=counts["P0"], p1=counts["P1"], p2=counts["P2"], p3=counts["P3"],
        caveats=f'<ul class="caveats">{caveats}</ul>' if caveats else "",
        rows="".join(rows), goals="".join(goals_html), nav="".join(nav), clusters="".join(cl_html),
        cons_md=f'<div class="md">{esc(cons_md)}</div>' if cons_md else "", cons=cons_html(),
        key=esc(re.sub(r"\W+", "-", s["app"] + "-" + s.get("date", "")).lower()))
    if o.lang == "en":
        page = page.replace('<html lang="de">', '<html lang="en">')
        for de, en in EN:
            page = page.replace(de, en)
    with open(os.path.join(out, "index.html"), "w") as f:
        f.write(page)
    print(os.path.join(out, "index.html"), f"({len(s['screens'])} screens, {len(s['goals'])} goals, {len(crit)} critiques)")


# Page chrome in English. Longer phrases first so shorter ones don't split them.
EN = [
    ("Jeder Ablauf ist ein Storyboard: jede Karte zeigt den Screen, auf dem der Schritt passierte, mit einer nummerierten Markierung an der Stelle des Tipps. Gezählt wird jede Interaktion außer Texteingabe. Unter jedem Ablauf, Screen und jeder Regel ist Platz für deine Notizen; sie speichern im Browser und lassen sich als Markdown exportieren.",
     "Each workflow is a storyboard: every card shows the screen the step happened on, with a numbered marker where the tap landed. Every interaction except typing text is counted. Every workflow, screen and rule has room for your notes; they save in this browser and export as Markdown."),
    ("Klick auf eine Karte springt zur Kritik des Screens; dort führt „Verwendet in\" zurück.", "Click a card to jump to that screen's critique; its \"Used in\" line leads back."),
    ("Browser-Speicher nicht verfügbar – bitte exportieren", "Browser storage unavailable, please export"),
    ("Kopieren nicht erlaubt – bitte exportieren", "Copying not allowed, please export"),
    ("Deine Notizen zu diesem Ablauf", "Your notes on this workflow"),
    ("Keine Konsistenzanalyse vorhanden.", "No consistency analysis yet."),
    ("Konsistenz über alle Screens", "Consistency across screens"),
    ("Notizen exportieren (.md)", "Export notes (.md)"),
    ("Deine Gesamteinschätzung", "Your overall view"),
    ("Größte Inkonsistenzen", "Biggest inconsistencies"),
    ("Einverstanden? Anpassen?", "Agree? Change?"),
    ("Ziele als Storyboards", "Goals as storyboards"),
    ("Konsistenz & Regeln", "Consistency & rules"),
    ("Gesamteinschätzung", "Overall view"),
    ("Platzierungsregeln", "Placement rules"),
    ("Keine Einzelkritik.", "No critique for this screen."),
    ("Notizen kopieren", "Copy notes"),
    ("Deine Gedanken", "Your thoughts"),
    ("Weitere Screens", "Other screens"),
    ("Verwendet in: ", "Used in: "),
    ("Export erstellt", "Export created"),
    ("zählt nicht", "not counted"),
    ("Interaktionen", "interactions"),
    ("Gespeichert", "Saved"),
    ("Bestätigung", "Confirmation"),
    ("Abläufe", "Workflows"), ("Gesamtbild", "Big picture"), ("Inhalt", "Contents"),
    ("Aufgabe", "Task"), ("Fazit", "Verdict"), ("Ideal", "Ideal"), ("ideal ", "ideal "),
    (">Ziel<", ">Goal<"), ("Ziele</span>", "goals</span>"), ("Screens</span>", "screens</span>"),
    ("Kontext", "Context"), ("Stil", "Style"), ("Stärken", "Strengths"), ("Befunde", "Findings"),
    ("Schritt ", "step "), (">auf <", ">on <"), (">gut<", ">good<"), ("Heute: ", "Today: "),
    (" – Notizen", " – notes"), ("Kopiert", "Copied"),
    ("Sprache", "Language"), ("Kontrolle", "Control"), ("Konsistenz", "Consistency"),
    ("Fehler vermeiden", "Error prevention"), ("Erkennen", "Recognition"), ("Effizienz", "Efficiency"),
    ("Reduktion", "Minimalism"), ("Fehler beheben", "Error recovery"), ("Hilfe", "Help"),
    ("deep-dive-notizen.md", "deep-dive-notes.md"),
]

TEMPLATE = """<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{app} Deep Dive {date}</title>
<style>
:root{{--ground:#F3F4F6;--paper:#fff;--ink:#16191E;--muted:#5D6470;--line:#DDE1E7;--accent:#0B63CE;--soft:#E6EFFB;
--p0:#B3261E;--p1:#C4561A;--p2:#8A6D00;--p3:#6B7280;--good:#1F7A45;--note:#FFFBEA;--noteline:#E9DCA0;color-scheme:light}}
@media (prefers-color-scheme:dark){{:root{{--ground:#111317;--paper:#1A1D22;--ink:#E8EAED;--muted:#9BA3AF;--line:#2C3037;--accent:#5AA2FF;--soft:#16263B;
--p0:#FF7B72;--p1:#FF9E5E;--p2:#E3C354;--p3:#9CA3AF;--good:#5BD08A;--note:#221F14;--noteline:#4A4226;color-scheme:dark}}}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--ground);color:var(--ink);font:16px/1.5 -apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}}
a{{color:var(--accent)}} .num,.sid,.gid,.rid,.count,.mark{{font-family:ui-monospace,Menlo,Consolas,monospace;font-variant-numeric:tabular-nums}}
.layout{{display:grid;grid-template-columns:230px minmax(0,1fr);gap:32px;max-width:1560px;margin:0 auto;padding-block:24px;padding-inline:20px}}
nav{{position:sticky;top:16px;align-self:start;display:flex;flex-direction:column;gap:2px;font-size:14px}}
nav a{{text-decoration:none;color:var(--ink);padding:6px 8px;border-radius:6px}} nav a:hover{{background:var(--soft)}} nav small{{color:var(--muted)}}
nav .grp{{margin-top:12px;color:var(--muted);font-size:12px;letter-spacing:.06em;text-transform:uppercase;padding-inline:8px}}
button{{font:inherit;font-size:14px;padding:8px 12px;border-radius:8px;border:1px solid var(--line);background:var(--paper);color:var(--ink);cursor:pointer;margin-top:6px}}
button.primary{{background:var(--accent);border-color:var(--accent);color:#fff}} #saved{{font-size:12px;color:var(--muted);min-height:1.2em}}
:focus-visible{{outline:2px solid var(--accent);outline-offset:2px}}
main{{min-width:0;display:flex;flex-direction:column;gap:40px}}
h1{{font-size:32px;margin:0 0 8px;text-wrap:balance}} h2{{font-size:25px;margin:0;display:flex;gap:10px;align-items:baseline}} h3{{font-size:19px;margin:0}} h4{{font-size:17px;margin:0}}
h5{{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin:14px 0 4px}}
.sub,.intent,.meta,.used,.job{{color:var(--muted)}} .ck,.gid{{background:var(--ink);color:var(--ground);border-radius:6px;padding:0 7px;font-size:15px;margin-right:8px}}
.box{{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:20px 24px}}
.pills{{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}} .pill{{border:1px solid var(--line);border-radius:999px;padding:3px 10px;font-size:13px;margin-right:6px}}
.tw{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;font-size:14px;background:var(--paper)}}
th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}} th{{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}}
.goal{{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:18px 20px;display:flex;flex-direction:column;gap:8px}}
.goal header{{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:baseline;justify-content:space-between}}
.board{{list-style:none;margin:0;padding:4px 2px 12px;display:grid;grid-auto-flow:column;grid-auto-columns:minmax(170px,190px);gap:14px;overflow-x:auto;scroll-snap-type:x proximity}}
.step{{scroll-margin:16px;scroll-snap-align:start;display:flex;flex-direction:column;gap:8px}}
.frame{{position:relative;display:block;border-radius:16px;overflow:hidden;border:1px solid var(--line);background:var(--ground)}}
.frame img{{width:100%;height:100%;object-fit:cover;display:block}}
.mark{{position:absolute;transform:translate(-50%,-50%);width:26px;height:26px;border-radius:50%;background:var(--accent);color:#fff;font-size:12px;font-weight:700;
display:grid;place-items:center;box-shadow:0 0 0 3px rgba(255,255,255,.9),0 2px 8px rgba(0,0,0,.35)}}
.mark.long-press{{background:#7C3AED}} .mark.swipe,.mark.drag{{background:#0E9F6E}} .mark.system{{background:var(--p3)}} .mark.end{{width:12px;height:12px;background:#0E9F6E}}
.arrow{{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}} .arrow line{{stroke:#0E9F6E;stroke-width:3;stroke-dasharray:6 4}}
.step.has-finding .frame{{border-color:var(--p1);border-width:2px}}
.cap{{font-size:14px;display:flex;flex-direction:column;gap:2px}} .cap p{{margin:0}} .caphead{{display:flex;gap:8px;align-items:center}}
.count{{background:var(--soft);color:var(--accent);border-radius:5px;padding:1px 7px;font-weight:700}} .count.off{{color:var(--muted);background:var(--ground)}}
.act{{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.05em}} .lbl{{font-weight:600}} .stnote{{color:var(--muted)}} .on{{font-size:12px;color:var(--muted)}}
.finding{{margin-top:4px!important}}
.verdict{{margin:0;font-weight:600}}
.cluster{{display:flex;flex-direction:column;gap:16px}}
.screen{{scroll-margin:16px;display:grid;grid-template-columns:240px minmax(0,1fr) minmax(220px,300px);gap:24px;background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:20px}}
.shot img{{width:100%;border-radius:16px;border:1px solid var(--line);display:block}} .crit p{{margin:4px 0}} .crit header{{display:flex;gap:10px;align-items:baseline}} .sid{{font-size:12px;color:var(--muted)}}
ul.issues{{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:10px}} ul.issues li{{display:grid;grid-template-columns:auto 1fr;gap:10px}}
ul.issues p{{color:var(--muted);font-size:15px}} ul.issues p.fix{{color:var(--ink)}} .viol{{color:var(--p1)!important}}
.sev{{display:inline-block;font:700 11px/1 ui-monospace,Menlo,monospace;padding:4px 6px;border-radius:5px;color:#fff;background:var(--p3)}}
.sev.p0{{background:var(--p0)}}.sev.p1{{background:var(--p1)}}.sev.p2{{background:var(--p2)}}.sev.good{{background:var(--good)}}
.rid{{background:var(--soft);color:var(--accent);border-radius:5px;padding:3px 6px;font-size:12px;align-self:start}}
.heur{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:4px;margin-top:12px}} .h{{background:var(--ground);border-radius:6px;padding:4px 6px;display:flex;flex-direction:column}}
.h i{{font:700 14px ui-monospace,Menlo,monospace;font-style:normal}} .h em{{font-style:normal;font-size:11px;color:var(--muted)}}
.h0 i,.h1 i{{color:var(--p0)}} .h2 i{{color:var(--p1)}} .h4 i{{color:var(--good)}}
.mine{{display:flex;flex-direction:column;gap:6px}} .notelabel{{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}}
textarea.note{{width:100%;font:inherit;font-size:15px;background:var(--note);color:var(--ink);border:1px solid var(--noteline);border-radius:10px;padding:10px 12px;resize:vertical}}
.mine textarea{{flex:1;min-height:170px}} details{{background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin-top:8px}}
.md{{white-space:pre-wrap;max-width:90ch}} .caveats{{color:var(--muted);font-size:15px}}
@media (max-width:1100px){{.screen{{grid-template-columns:200px minmax(0,1fr)}}.mine{{grid-column:1/-1}}}}
@media (max-width:760px){{.layout{{grid-template-columns:1fr}}nav{{position:static}}.screen{{grid-template-columns:1fr}}.shot{{max-width:260px}}.heur{{grid-template-columns:repeat(2,1fr)}}}}
@media (prefers-reduced-motion:no-preference){{html{{scroll-behavior:smooth}}}}
</style></head><body>
<div class="layout">
<nav aria-label="Inhalt"><a href="#top"><strong>{app} Deep Dive</strong></a>
<span class="grp">Abläufe</span><a href="#goals">Ziele als Storyboards</a>
<span class="grp">Screens</span>{nav}
<span class="grp">Gesamtbild</span><a href="#consistency">Konsistenz & Regeln</a><a href="#overall">Gesamteinschätzung</a>
<button class="primary" id="export" type="button">Notizen exportieren (.md)</button><button id="copy" type="button">Notizen kopieren</button><span id="saved" role="status"></span></nav>
<main id="top">
<section class="box"><h1>{app} Deep Dive {date}</h1>
<p>{device} · Build {build}. Jeder Ablauf ist ein Storyboard: jede Karte zeigt den Screen, auf dem der Schritt passierte, mit einer nummerierten Markierung an der Stelle des Tipps. Gezählt wird jede Interaktion außer Texteingabe. Unter jedem Ablauf, Screen und jeder Regel ist Platz für deine Notizen; sie speichern im Browser und lassen sich als Markdown exportieren.</p>
{caveats}
<div class="pills"><span class="pill">{n_screens} Screens</span><span class="pill">{n_goals} Ziele</span><span class="pill">P0 {p0}</span><span class="pill">P1 {p1}</span><span class="pill">P2 {p2}</span><span class="pill">P3 {p3}</span></div></section>
<section id="goals"><h2>Ziele als Storyboards</h2><p class="sub">Klick auf eine Karte springt zur Kritik des Screens; dort führt „Verwendet in" zurück.</p>
<div class="tw box"><table><thead><tr><th>Ziel</th><th>Aufgabe</th><th>Interaktionen</th><th>Ideal</th><th>Fazit</th></tr></thead><tbody>{rows}</tbody></table></div>
<div style="display:flex;flex-direction:column;gap:18px;margin-top:18px">{goals}</div></section>
{clusters}
<section id="consistency"><h2>Konsistenz über alle Screens</h2><div class="box" style="margin-top:12px">{cons_md}{cons}</div></section>
<section id="overall" class="goal"><h2>Deine Gesamteinschätzung</h2><textarea class="note" id="n-overall" data-key="overall" data-title="Gesamteinschätzung" rows="8" aria-label="Gesamteinschätzung"></textarea></section>
</main></div>
<script>
(function(){{
 const P="deep-dive:{key}:",notes=[...document.querySelectorAll("textarea.note")],saved=document.getElementById("saved");
 const rd=k=>{{try{{return localStorage.getItem(P+k)||""}}catch(e){{return""}}}}, wr=(k,v)=>{{try{{localStorage.setItem(P+k,v);return true}}catch(e){{return false}}}};
 notes.forEach(t=>{{t.value=rd(t.dataset.key);let h;t.addEventListener("input",()=>{{clearTimeout(h);h=setTimeout(()=>saved.textContent=wr(t.dataset.key,t.value)?"Gespeichert":"Browser-Speicher nicht verfügbar – bitte exportieren",300)}})}});
 const md=()=>{{const o=["# {app} Deep Dive {date} – Notizen",""];notes.forEach(t=>{{const v=t.value.trim();if(v)o.push("## "+t.dataset.title,"",v,"")}});return o.join("\\n")}};
 document.getElementById("export").onclick=()=>{{const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([md()],{{type:"text/markdown"}}));a.download="deep-dive-notizen.md";document.body.appendChild(a);a.click();a.remove();saved.textContent="Export erstellt"}};
 document.getElementById("copy").onclick=()=>navigator.clipboard.writeText(md()).then(()=>saved.textContent="Kopiert",()=>saved.textContent="Kopieren nicht erlaubt – bitte exportieren");
}})();
</script></body></html>
"""

if __name__ == "__main__":
    main()
