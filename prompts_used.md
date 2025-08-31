# LLM Prompts Used

**Dataset provided to model:** `games_final.csv`  
**Location on disk:** `/Users/hridayamurudkar/Downloads/period_03/data/games_final.csv`  
**Instruction to model:** *Use only this CSV. Show calculations. If data is missing, say so. Do not use outside knowledge.*

---

## System Prompt
You are a careful sports analyst. Use ONLY the CSV I provide. If a calculation requires data not in the CSV, say so. Show your work with small tables and the final answer clearly.

## Prompt 1 — Basics
Using `games_final.csv` (columns: `date, opponent, venue {Home/Away/Neutral}, result {W/L}, goals_for, goals_against`):
1) How many games did we play?  
2) What is the W–L record?  
3) What are average goals for and against?

## Prompt 2 — One-goal games
List all one-goal losses (date, opponent, score).

## Prompt 3 — What-if (+2 GF) and (−2 GA)
Simulate across all games:
- Scenario A: add **+2** to `goals_for` in every game.  
- Scenario B: subtract **2** from `goals_against` in every game.  
For each: which losses flip to wins and what is the new W–L? Show the flipped games.

## Prompt 4 — Sensitivity (d = 1..4)
For d = 1..4, report how many losses would flip under:
- **+d GF**,
- **−d GA**,
- and the **best split** (+x GF / −y GA, x+y=d).

## Prompt 5 — Coach recommendation
Given the sensitivity results, if the goal is **+2 more wins next season**, should we emphasize **offense** or **defense**? Justify using the flipping analysis. Keep it to 3–5 sentences.

## Prompt 6 — Data QA
Recompute wins by checking `goals_for > goals_against` and confirm it matches the `result` column; list any mismatches.

## Prompt 7 — Simple visualization
Produce a line chart of `goals_for` and `goals_against` by date. If charts aren’t supported, output a small table instead.

---

**Model(s) used:** (fill in: ChatGPT / Claude / Copilot + version)  
**Date run:** (fill in)  
**Files uploaded to the model:** `games_final.csv` (and optionally PDF for reference)  
**Outputs saved as:** `llm_answers_after_fix.pdf` (screenshots/exports)
