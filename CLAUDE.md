# Entheocast — Claude Instructions

## ROADMAP.md is the SSOT

`ROADMAP.md` is the single source of truth for all project progress.

- Read it at the start of every session.
- Check off tasks the moment they complete.
- If a task expands into subtasks, add subsections to the roadmap inline — never in a separate file or ticket.
- Never report a task as done unless its checkbox is checked in `ROADMAP.md`.
- If work reveals a new required step, add it to the roadmap before doing it.

## Project

Entheocast is a static site + automated pipeline that aggregates psychedelic clinical trials, studies, and regulatory updates into a structured open dataset, served on GitHub Pages. See `PRD.md` for full spec.

## Stack

- Python pipeline: `uv` (`cd pipeline && uv sync && uv run python run.py`)
- Site: static HTML + vanilla CSS + vanilla JS — no framework, no database
- GitHub Actions: weekly cron (Sunday 8pm ET)
- APIs: PubMed, ClinicalTrials.gov, Semantic Scholar, bioRxiv; Tavily search; Jina Reader; Mimo via OpenRouter

## Ordering Constraint

Pipeline before site. Do not build site pages until `data/entries.json` has real data.
Phase order in `ROADMAP.md` is correct — follow it. Skip-ahead is a backtrack risk.

## Environment

Required env vars: `TAVILY_API_KEY`, `OPENROUTER_API_KEY`. Read from `.env`, never hardcode.

## Style Decision Gate

Per PRD: present 3 `index.html` style variants before building all pages. Do not build `style.css` or other pages until user picks. This is a **blocking checkpoint**.

## What NOT to Build (v1)

Newsletter, custom domain, podcast audio, React/Next.js, database, AI-written prose, user accounts.
