#!/usr/bin/env python3
"""
One-click profile updater — MANUAL ONLY, not scheduled, not a GitHub Action.

Run from the profile repo clone (yousufkidiya17/yousufkidiya17) on your PC:
    python scripts/auto_update_profile.py

What it updates in one go:
  1. Contribution graph — runs scripts/fetch_contributions.py + render_heatmap_svg.py,
     copies the new heatmap to the dark version too.
  2. Project cards — refreshes stars, forks and language on all featured repo cards
     (light + dark) from live GitHub data via `gh repo list`.
  3. Repo count — recounts all your repos, updates the "total project repositories"
     line in README and regenerates the "All Repositories" link list.
  4. Commits + pushes the result to main.

It does NOT re-enable the disabled GitHub Actions workflow. Run it only when you say so.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEATURED = [
    "tally-mcp", "aiml-journey", "aetherix-ai", "smart-trading-scanner",
    "OPEN-HERMES", "hermeszen-adk", "train-travel-assistant", "opencode-local-api",
    "crawlpedia-cyber-entities", "agent-guardrails",
]
PROFILE_REPO = "yousufkidiya17"


def run(cmd, **kw):
    print("+", " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT, check=True, **kw)


def get_repos():
    out = subprocess.run(
        ["gh", "repo", "list", PROFILE_REPO, "--limit", "100",
         "--json", "name,stargazerCount,forkCount,primaryLanguage"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    return json.loads(out.stdout)


def update_cards(repos):
    by_name = {r["name"]: r for r in repos}
    footer_re = re.compile(r'<text x="16" y="184"[^>]*>.*?</text>\n?', re.S)
    for name in FEATURED:
        repo = by_name.get(name)
        if not repo:
            print(f"skip card (repo not found): {name}")
            continue
        stars = repo.get("stargazerCount", 0)
        forks = repo.get("forkCount", 0)
        lang = (repo.get("primaryLanguage") or {}).get("name", "")
        for suffix, color in [("", "#6a6a6a"), ("-dark", "#7d8590")]:
            p = ROOT / f"repo-{name}{suffix}.svg"
            if not p.exists():
                print(f"skip card file (missing): {p.name}")
                continue
            t = p.read_text(encoding="utf-8")
            footer = (
                f'<text x="16" y="184" font-family="-apple-system,\'Segoe UI\','
                f'Helvetica,Arial,sans-serif" font-size="13" fill="{color}">'
                f"\u2605 {stars}  \u2022  Forks {forks}  \u2022  {lang}</text>\n"
            )
            if footer_re.search(t):
                t = footer_re.sub(footer, t, count=1)
            else:
                t = t.replace("</svg>", footer + "</svg>")
            p.write_text(t, encoding="utf-8")
            print(f"card updated: {p.name} -> stars {stars}, forks {forks}, {lang}")


def update_readme(repos):
    readme = ROOT / "README.md"
    t = readme.read_text(encoding="utf-8")
    total = len(repos)
    projects = total - 1 if PROFILE_REPO in {r["name"] for r in repos} else total
    featured = [n for n in FEATURED if n in {r["name"] for r in repos}]
    # Count line
    t, n1 = re.subn(
        r"\d+ featured projects below — total \*\*\d+ project repositories\*\* \(\d+ including this profile repo\)\.",
        f"{len(featured)} featured projects below — total **{projects} project repositories** ({total} including this profile repo).",
        t, count=1,
    )
    if n1 == 0:
        print("WARN: repo-count line not found, not updated")
    # All Repositories section
    others = [r["name"] for r in repos
              if r["name"] not in featured and r["name"] != PROFILE_REPO]
    links = ", ".join(
        f"[{r}](https://github.com/yousufkidiya17/{r})" for r in others)
    section = f"### All Repositories\n\n{links}\n"
    t, n2 = re.subn(
        r"### All Repositories\n\n.*?(?=\n## )", section, t, count=1, flags=re.S)
    if n2 == 0:
        print("WARN: All Repositories section not found, not updated")
    readme.write_text(t, encoding="utf-8", newline="\n")
    print(f"README updated: total {total}, projects {projects}, featured {len(featured)}, others {len(others)}")


def update_graph():
    run([sys.executable, "scripts/fetch_contributions.py"])
    run([sys.executable, "scripts/render_heatmap_svg.py"])
    src = ROOT / "contrib-heatmap.svg"
    dst = ROOT / "contrib-heatmap-dark.svg"
    if src.exists():
        shutil.copyfile(src, dst)
        print("heatmap copied to dark version")


def main():
    repos = get_repos()
    print(f"repos found: {len(repos)}")
    update_cards(repos)
    update_readme(repos)
    update_graph()
    run(["git", "add", "README.md", "repo-*.svg",
         "contrib-heatmap.svg", "contrib-heatmap-dark.svg",
         "data/contributions.json", "scripts/auto_update_profile.py"])
    status = subprocess.run(["git", "status", "--short"],
                            cwd=ROOT, capture_output=True, text=True).stdout
    print(status or "(no changes)")
    if not status.strip():
        print("Nothing to update — already up to date.")
        return
    run(["git", "commit", "-m",
         "chore: auto-update profile graph, cards and repo count"])
    run(["git", "push", "origin", "main"])
    print("DONE: profile auto-update pushed.")


if __name__ == "__main__":
    main()
