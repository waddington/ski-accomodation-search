# Ski chalet search: project instructions

**Start every session by reading `HANDOFF.md`.** It has the brief, the current state, architecture, coverage, known issues and next steps. For collector-agent work, also read `chalets/COLLECTOR_BRIEF.md`.

## Standing rules (from the user)

- **Outputs are files in this repo.** Never Claude Docs or Artifacts.
- **Collect everything; filter with scripts.** Raw CSVs in `chalets/raw/` → `chalets/build_chalets.py` → filtered CSVs. Never drop data at collection time.
- **Never block data collection on a question.** Restart idle agents first, take a sensible default, log it, and ask alongside.
- **Parallel agents:** about 4–5 max. 8+ exhausted the Claude usage limit in about 2.5 h. Each agent does one thing at a time, and tasks are claimed atomically via `tools/queue.py claim --lane=…`.
- **Websites:** max 2 concurrent requests per site across all agents (enforced in `tools/scrapers/common.py`). Stop on 403/429/captcha and log it.
- **Prefer LLM-free scrapers** (`tools/scrapers/`, READY ones) + 2 browser spot-checks over LLM browsing.
- **Priority:** France first; abroad after; Dolomiti Superski villages last.
- **Brief:** catered (hot tub nice-to-have), 8–10 people, 20–27 Mar 2027, about £750pp accommodation + catering (no flights), major linked ski area.
- **Git:** follow `~/.claude/git-workflow.md` (worktree + branch + PR; the user merges). Never commit `chalets/images/` (2.9 GB originals; the site uses resized copies in `docs/`). Check `git diff --cached --stat` before committing.
- **Repo is public.** Public contact details in the raw data are OK (user's decision, including the openbooking API key). `docs/` must stay redacted: always rebuild it with `python3 tools/build_static.py`, which runs `tools/redact_static.py`.
- **Live dashboard:** `python3 dashboard/serve.py` → http://localhost:8777/. Static site: `docs/` → https://waddington.github.io/ski-accomodation-search/
