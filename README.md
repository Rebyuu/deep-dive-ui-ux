# deep-dive-ui-ux

A skill for Claude (Claude Code, the Claude app, or any agent that reads Agent Skills) that performs a hands-on UI/UX deep dive of a running app and turns it into one review page you can annotate.

Claude drives your real app (an iOS simulator, an Android emulator or a web app in a browser) as a realistic user and:

- **walks concrete goals** such as "create a project", "file the first defect with a new trade" or "delete a company", the way your real users would;
- **screenshots every screen and counts every interaction** (typing text doesn't count), including wrong turns, hidden gestures and system prompts;
- **critiques each screen** for its job and its users: verdict, strengths, issues ranked P0–P3 with a concrete fix, Nielsen heuristics 0–4, and an inventory of every control;
- **looks across all screens** to find where add, delete, rename, confirm, cancel, settings, filter and status controls live, and proposes one consistent placement system (8–14 rules);
- **builds a review page** where every workflow is a storyboard of its own screenshots.

## What the report looks like

- **Goals as storyboards.** Each goal is a strip of step cards. Every card shows the screen the step happened on, with a numbered marker exactly where the tap landed (an arrow for swipes), the action, a running interaction count and any finding. The overview table shows logged vs. ideal interactions per goal, so wasted taps are visible.
- **Screens by area.** Each screen has its critique and a *Used in* line linking back to the workflow steps that touched it, so text and screenshot are never far apart.
- **Consistency.** The proposed placement rules, the biggest inconsistencies, and an action-by-screen matrix.
- **Your notes.** A notes field on every goal, screen and rule. They save in your browser, and *Export notes* gives you a Markdown file to hand back to Claude as the input for a UI/UX guideline or redesign.

The page is in English; `--lang de` switches its labels to German (your content stays as written).

## Why storyboards

The first version of this workflow produced a written log of each workflow and, separately, a gallery of screenshots. Readers had to match "tap 4: Rename" to the right image in their head. This skill logs every step as data that points at its screenshot and tap coordinates, so the report can put them together.

## Install

Claude Code (personal skills):

```bash
git clone https://github.com/Rebyuu/deep-dive-ui-ux ~/.claude/skills/deep-dive-ui-ux
```

For a single project, clone it into `.claude/skills/deep-dive-ui-ux` inside the repository instead. In the Claude app, upload the folder as a skill.

## Use

Ask in your own words, for example:

> Walk through my app in the simulator like a site engineer who starts pinning right away. Count the taps for creating a project, filing defects and managing trades, and build me a page where I can comment on every screen.

The skill triggers on requests to audit, review, critique or walk through an app's UX, count clicks, document every screen, or find inconsistent control placement.

## What's inside

```
SKILL.md                      the workflow Claude follows
references/driving.md         driving iOS / Android / web, coordinates, tool pitfalls
references/critique-brief.md  output contract for per-screen critique agents
references/consistency-brief.md  output contract for the cross-screen analysis
scripts/session.py            structured log: goals, screenshots, steps with tap points, findings
scripts/build_report.py       builds the review page (--inline, --lang en|de, --storage-key)
evals/evals.json              test prompts for iterating on the skill
```

The scripts need only Python 3. Image conversion uses `sips` on macOS, or Pillow if installed; otherwise the PNGs are copied as they are. Screenshots from the iOS simulator need Xcode's `simctl`.

## Privacy

Deep dives often run on real data. The skill keeps sensitive sessions local: screenshots and the report go into a gitignored folder, real documents are never uploaded to third-party services, and the report isn't published as a hosted page unless it contains no sensitive data.

## License

MIT
