---
name: deep-dive-ui-ux
description: Hands-on UI/UX deep dive of a running app. Claude drives the real app (iOS simulator, Android emulator, or a web app in a browser) as a realistic user, walks concrete goals such as "create a project" or "delete a trade", screenshots every screen, counts every tap, critiques each screen, maps where add/delete/edit/confirm controls sit across screens, and builds one review page where each workflow is a storyboard of its own screenshots with tap markers and each screen has a notes field for the owner. Use this whenever someone wants to audit, review, critique, test or walk through the UX/UI of their app end to end, count clicks for tasks, find inconsistent control placement, document every screen, or prepare a baseline before a UI/UX redesign, even if they don't say "deep dive".
---

# Deep dive UI/UX

A deep dive answers three questions about a real, running app:

1. **Workflows:** how many interactions does each real goal take, and where does the user hesitate, mis-tap or get lost?
2. **Screens:** what is wrong or right on each screen, judged for this product's users?
3. **System:** do similar actions (add, delete, rename, confirm, cancel, settings, filter, status) live in the same place and look the same across similar screens?

The output is one review page the owner scrolls through and annotates. The page's value depends on one thing above all: **every workflow step must be tied to the screenshot it happened on**, so the reader sees what the tester saw at each tap. A workflow told in text beside a separate gallery of screenshots forces the reader to match them up in their head. Don't build that. The bundled scripts enforce the connection: steps are logged as data that points at screenshots and tap coordinates, and the report renders each goal as a storyboard.

## 0. Before you touch the app

Read the product context: PRODUCT.md, DESIGN.md, README, the UI guidelines, or ask. You are simulating a real user, and a critique is only as good as your picture of who they are and where they work.

Agree the goals with the user, or propose them from the product: 8–12 concrete goals, each a job a real user does, e.g. "create a project with four levels", "file a defect with a new trade", "change a defect's status", "filter the plan", "rename / delete / add master data". Include at least one setup goal, the core loop, one management goal (edit, delete, add) and one output goal (export or share). If the user describes how the persona behaves (e.g. "starts pinning right away without setting up trades first"), play it that way; that is where the real friction shows.

**Sensitive data.** If test content includes real client data (their documents, plans, names), keep everything local: store screenshots and the report in a gitignored folder, never upload the documents to third-party services (for generated stand-ins, describe the *style* in words only), and do not publish the report as a hosted page. Say so to the user.

**Test data.** Create realistic data as the persona would. Generated stand-ins (images, plans, documents) are fine when real ones are missing; state what is synthetic in the report.

## 1. Set up the session

Create a working directory (inside a gitignored folder if the data is sensitive) and initialise the session file:

```bash
python <skill>/scripts/session.py init <dir> --app "<name>" --device "<device>" --width <pt> --height <pt> --build "<version or commit>"
```

`--width/--height` are the screen size in the coordinate system you tap in (points on iOS, dp on Android, CSS px on web). The report uses them to place tap markers on screenshots.

Driving the app, per platform: see `references/driving.md` (simulator/emulator/browser tips, coordinate scaling, recurring tool pitfalls like typing artifacts and missing backspace).

## 2. Walk each goal, logging as you go

This is the core loop. Do it for every interaction, in this order:

1. **Screenshot the screen you are about to act on**, if you haven't captured this exact state yet: `session.py shot <dir> <screen-id> --title "<name>" --cluster <A|B|…>` (ids: `NN-short-name`, zero-padded, in order of capture). It copies the image into the session and registers it.
2. **Act.** Tap, swipe, long-press, type.
3. **Log the step immediately**, pointing at the screen you acted on and where:
   ```bash
   python <skill>/scripts/session.py step <dir> <goal-id> --screen <screen-id> --action tap --x 201 --y 603 --label "New project" [--no-count] [--finding P1 "…"] [--note "…"]
   ```
   `--action` is tap | long-press | swipe | type | drag | system. Typing text does not count as an interaction (`type` is logged with `--no-count` automatically). A tap only needed because of a test-tool problem gets `--no-count --note "tool"`. For swipes and drags pass `--x2 --y2`.
4. When something noteworthy happens (confusion, a wrong turn, a silent data change, a good pattern), attach it to the step as `--finding <P0-P3|good> "<what and why>"`, not in a separate notebook. Findings live where they happened.

Open a goal before its first step and close it after its last:

```bash
python <skill>/scripts/session.py goal <dir> G4 "File the first defect with new trade and company" --intent "What the user wants to achieve"
python <skill>/scripts/session.py close <dir> G4 --verdict "One-sentence summary of how it went" --ideal <n>
```

`--ideal` is the minimum interactions for the goal on the best path you found; the report shows logged vs ideal, so wasted taps (discovery, mis-taps) are visible.

**Repetition.** When a flow repeats with no new UX (the same form on another level), don't re-document it. Log it once as a goal and add one step with `--note "repeated on UG1, ZG1, OG1: same flow, 5 interactions each"`.

**Explore every surface.** Beyond the goals, capture each menu, sheet, alert, confirmation, empty state and settings screen at least once, including long-press menus and swipe actions (the hidden ones are often the findings). Use `session.py shot` for these too; they appear in the screen clusters.

**Clusters** group screens by area (e.g. A Setup, B Core loop, C Review & output, D Management & settings). Declare them once: `session.py cluster <dir> A "Setup" --about "Create project, levels, plans"`.

## 3. Critique screens in parallel while you keep testing

Don't wait until the end. After each cluster is captured, spawn a subagent to critique it while you walk the next goals (it is the slowest part and runs independently). Give each critique agent:

- `references/critique-brief.md` (the output contract: per screen job, verdict, strengths, issues with severity and fix, heuristic scores, and a controls inventory),
- the screen ids and the session directory,
- the product context files, and platform rules if a design skill provides them (e.g. an `impeccable` critique or iOS reference),
- the session file, so it can read which goal steps touched each screen.

Each agent writes `critique/<cluster>.json` into the session directory.

## 4. Look across screens

When all clusters are critiqued, spawn one agent with `references/consistency-brief.md`. It reads every controls inventory plus the screenshots and produces `critique/consistency.json`: an action-by-screen matrix, screen families that should behave alike, 8–14 placement rules forming one system, and the top inconsistencies. This is often the most useful part for the next redesign; don't skip it.

## 5. Build the report

```bash
python <skill>/scripts/build_report.py <dir> [--out <dir>/report] [--inline] [--lang en|de] [--storage-key KEY]
```

The page is English by default; pass `--lang de` for a German page (translation covers the page's own labels; content stays as written). `--inline` makes one self-contained file with the screenshots embedded. When rebuilding a report the owner has already annotated, reuse its `--storage-key` and write to the same path so their notes reappear.

It produces `index.html` with:

- an overview (setup, caveats, severity counts, tap table: logged vs ideal per goal),
- **each goal as a storyboard**: a horizontal strip of step cards, each showing the screenshot it happened on with a numbered marker at the tap point (and an arrow for swipes), the action, a running interaction count and any finding. Clicking a card jumps to that screen's critique.
- screens by cluster, each with its critique **and a "used in" line linking back to the goal steps that touched it**,
- the consistency rules and matrix,
- a notes field on every goal, screen and rule (saved in the browser), and an export of all notes as Markdown for the owner to hand back.

Open it for the user locally. Only publish it (e.g. as a hosted artifact) when it contains no sensitive data.

## 6. Hand over

Tell the user in a few lines: what was tested (goals, screens, data), the most important findings (P0/P1 first), the tap counts that matter, the proposed placement rules, test-tool artifacts to ignore, and how to return their notes. Their annotated export is the input for the next step, usually a UI/UX guideline or a redesign plan.

## Severity scale

- **P0**: blocks the task or silently damages data (e.g. deleting something in use without warning).
- **P1**: costs real time or causes errors in the real usage context.
- **P2**: friction or inconsistency.
- **P3**: polish.
- **good**: a pattern worth keeping or copying elsewhere.

## Common mistakes

- Screenshots taken in bulk after the fact: they no longer match the steps. Capture before acting.
- Findings written as a list at the end: attach them to the step where they happened.
- Critiquing from memory of what a screen "usually" looks like: open the image.
- Counting tool mishaps as UX cost: log them with `--no-count --note tool`.
- Critique agents with no picture of the user: always pass the product context.
