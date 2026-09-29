#!/usr/bin/env python3
"""Structured log for a UI/UX deep dive.

Every workflow step points at the screenshot it happened on and the tap
coordinates, so the report can show each goal as a storyboard.

Commands:
  init    <dir> --app NAME --device NAME --width W --height H [--build B] [--date YYYY-MM-DD]
  cluster <dir> ID NAME [--about TEXT]
  shot    <dir> SCREEN_ID [--file PNG] [--title T] [--cluster C]
  goal    <dir> GOAL_ID TITLE [--intent TEXT]
  step    <dir> GOAL_ID --screen SCREEN_ID --action ACTION [--x X --y Y] [--x2 X --y2 Y]
          [--label L] [--note N] [--finding SEV TEXT]... [--no-count]
  close   <dir> GOAL_ID [--verdict TEXT] [--ideal N]
  caveat  <dir> TEXT
  status  <dir>

`shot` without --file captures from the booted iOS simulator (xcrun simctl);
on other platforms capture yourself and pass --file.
"""
import argparse, json, os, shutil, subprocess, sys, datetime

ACTIONS = {"tap", "long-press", "swipe", "type", "drag", "system"}
SEVERITIES = {"P0", "P1", "P2", "P3", "good"}


def path(d):
    return os.path.join(d, "session.json")


def load(d):
    with open(path(d)) as f:
        return json.load(f)


def save(d, s):
    tmp = path(d) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path(d))


def die(msg):
    print("error: " + msg, file=sys.stderr)
    sys.exit(2)


def find_goal(s, gid):
    for g in s["goals"]:
        if g["id"] == gid:
            return g
    die(f"goal {gid} not found; open it with `goal` first")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("init"); a.add_argument("dir"); a.add_argument("--app", required=True)
    a.add_argument("--device", required=True); a.add_argument("--width", type=float, required=True)
    a.add_argument("--height", type=float, required=True); a.add_argument("--build", default="")
    a.add_argument("--udid", default="", help="iOS simulator UDID used by `shot`")
    a.add_argument("--date", default="", help="session date, defaults to today")

    a = sub.add_parser("cluster"); a.add_argument("dir"); a.add_argument("id"); a.add_argument("name")
    a.add_argument("--about", default="")

    a = sub.add_parser("shot"); a.add_argument("dir"); a.add_argument("screen")
    a.add_argument("--file"); a.add_argument("--title", default=""); a.add_argument("--cluster", default="")

    a = sub.add_parser("goal"); a.add_argument("dir"); a.add_argument("id"); a.add_argument("title")
    a.add_argument("--intent", default="")

    a = sub.add_parser("step"); a.add_argument("dir"); a.add_argument("goal")
    a.add_argument("--screen", required=True); a.add_argument("--action", required=True)
    for k in ("x", "y", "x2", "y2"):
        a.add_argument("--" + k, type=float)
    a.add_argument("--label", default=""); a.add_argument("--note", default="")
    a.add_argument("--finding", nargs=2, metavar=("SEV", "TEXT"), action="append",
                   help="repeatable: one step can carry several findings")
    a.add_argument("--no-count", action="store_true")

    a = sub.add_parser("close"); a.add_argument("dir"); a.add_argument("goal")
    a.add_argument("--verdict", default=""); a.add_argument("--ideal", type=int)

    a = sub.add_parser("caveat"); a.add_argument("dir"); a.add_argument("text")
    a = sub.add_parser("status"); a.add_argument("dir")

    o = p.parse_args()
    d = o.dir

    if o.cmd == "init":
        os.makedirs(os.path.join(d, "shots"), exist_ok=True)
        os.makedirs(os.path.join(d, "critique"), exist_ok=True)
        if os.path.exists(path(d)):
            die("session.json already exists")
        save(d, {"app": o.app, "device": o.device, "width": o.width, "height": o.height, "build": o.build,
                 "udid": o.udid, "date": o.date or datetime.date.today().isoformat(), "caveats": [],
                 "clusters": [], "screens": [], "goals": []})
        print("initialised", path(d)); return

    s = load(d)

    if o.cmd == "cluster":
        s["clusters"] = [c for c in s["clusters"] if c["id"] != o.id] + [{"id": o.id, "name": o.name, "about": o.about}]

    elif o.cmd == "shot":
        dest = os.path.join(d, "shots", o.screen + ".png")
        if o.file:
            shutil.copyfile(o.file, dest)
        else:
            cmd = ["xcrun", "simctl", "io", s.get("udid") or "booted", "screenshot", dest]
            if subprocess.run(cmd, capture_output=True).returncode != 0:
                die("simulator capture failed; capture yourself and pass --file")
        entry = {"id": o.screen, "file": "shots/" + o.screen + ".png", "title": o.title, "cluster": o.cluster}
        s["screens"] = [x for x in s["screens"] if x["id"] != o.screen] + [entry]
        s["screens"].sort(key=lambda x: x["id"])
        print(dest)

    elif o.cmd == "goal":
        if any(g["id"] == o.id for g in s["goals"]):
            die(f"goal {o.id} exists")
        s["goals"].append({"id": o.id, "title": o.title, "intent": o.intent, "steps": [], "verdict": "", "ideal": None})

    elif o.cmd == "step":
        if o.action not in ACTIONS:
            die(f"action must be one of {sorted(ACTIONS)}")
        if not any(x["id"] == o.screen for x in s["screens"]):
            die(f"screen {o.screen} is not registered; capture it with `shot` before acting on it")
        g = find_goal(s, o.goal)
        st = {"n": len(g["steps"]) + 1, "screen": o.screen, "action": o.action, "label": o.label,
              "note": o.note, "counts": not o.no_count and o.action != "type"}
        for k in ("x", "y", "x2", "y2"):
            v = getattr(o, k)
            if v is not None:
                st[k] = v
        for sev, text in o.finding or []:
            if sev not in SEVERITIES:
                die(f"severity must be one of {sorted(SEVERITIES)}")
            st.setdefault("findings", []).append({"severity": sev, "text": text})
        g["steps"].append(st)
        n = sum(1 for x in g["steps"] if x["counts"])
        print(f"{o.goal} step {st['n']} logged ({n} interactions so far)")

    elif o.cmd == "close":
        g = find_goal(s, o.goal)
        g["verdict"] = o.verdict
        g["ideal"] = o.ideal
        n = sum(1 for x in g["steps"] if x["counts"])
        print(f"{o.goal} closed: {n} interactions logged" + (f", ideal {o.ideal}" if o.ideal else ""))

    elif o.cmd == "caveat":
        s["caveats"].append(o.text)

    elif o.cmd == "status":
        print(f"{s['app']} · {len(s['screens'])} screens · {len(s['goals'])} goals")
        for g in s["goals"]:
            n = sum(1 for x in g["steps"] if x["counts"])
            print(f"  {g['id']} {g['title']}: {len(g['steps'])} steps, {n} interactions")
        return

    save(d, s)


if __name__ == "__main__":
    main()
