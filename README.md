# Task_05_Descriptive_Stats
Here’s my concise report for this period.

# Summary of work this period

**Goal.** Take a small public dataset (SU Women’s Lacrosse season) and get an LLM to answer natural-language questions about it, while validating the answers with my own code.

**Data & tooling.**

* Source: SU Women’s Lacrosse season PDF (official stats/schedule).
* Set up a clean Python venv; installed `camelot-py`, `pdfminer.six`, `pandas`, `matplotlib`, Ghostscript; added OCR fallback with `ocrmypdf`.
* Created two reusable scripts:

  * `ocr_and_parse.py` — OCRs (if needed) and parses schedule lines into `games.csv`.
  * `clean_and_sensitivity.py` — cleans to `games_clean.csv` → exports `games_final.csv`; runs goal-swing sensitivity and writes a summary.

**Pipeline & debugging.**

* First pass over-parsed the PDF (41 “games” due to dates misread as scores).
  Fixes: stricter score regex (avoid 12-07-YYYY), realistic score bounds, season window, opponent sanity checks, de-dupes.
* Produced a clean season file (**initially 15 games → 6–9**).
  Cross-checked against the official PDF, found the season lists **19 games (10–9)**, so I updated parsing (two-line rows, neutral “vs” handling) and re-generated to include all games.
* Kept provenance by saving pre-fix vs post-fix outputs.

**Analyses & validation.**

* Computed record, GF/GA averages, goal differential per game.
* Sensitivity (“what if we want +2 wins?”): tested uniform goal swings.

  * With the 15-game cut: a **2-goal swing** flipped **3 one-goal losses** (Clemson 8–9, Johns Hopkins 13–14, at Yale 8–9).
  * Re-ran after correcting to the full 19; updated the flips and conclusions accordingly.
* Built plots: `goals_by_game.png` (GF/GA over time) and `goal_diff_by_game.png`.

**LLM work.**

* Prepared `games_final.csv` (tidy columns: date, opponent, venue, result, goals\_for, goals\_against).
* Crafted prompts that constrain the model to **use only the CSV** and **show its math** (logged in `llm/prompts_used.md`).
* Asked: games count, W-L, averages, one-goal losses, +2GF/−2GA simulations, and a coach recommendation.
* Compared the model’s outputs to my Python results and noted agreement/mismatches.

**What failed & lessons.**

* Environment hiccups (OpenCV wheel build; path/quoting on macOS; running Python code in zsh by mistake).
  Resolved with a dedicated venv, absolute paths, and heredoc blocks for Python.
* Parsing failures (dates mistaken for scores; split lines).
  Resolved with OCR first, safer regex, and two-line matching.

**Deliverables prepared (post-correction).**

* `data/games_clean.csv` (clean, full season)
* `data/games_final.csv` (LLM input)
* `outputs/flips_summary.txt`, `goals_by_game.png`, `goal_diff_by_game.png`
* `code/ocr_and_parse.py`, `code/clean_and_sensitivity.py`
* `llm/prompts_used.md` + screenshots/exports of the LLM answers after the fix
* Short write-up (methods, validation, coach recommendation, and next-steps)



If you want, I can turn this into a 1–2 page `report.md` with your updated season numbers dropped in.
