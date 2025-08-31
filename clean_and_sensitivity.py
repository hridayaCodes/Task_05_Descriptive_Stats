#!/usr/bin/env python3
import argparse, re
from pathlib import Path
import pandas as pd

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={
        'gf': 'goals_for',
        'ga': 'goals_against',
        'wl': 'result',
        'team': 'opponent'
    })
    return df

def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
    for c in ('goals_for','goals_against'):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    if 'result' in df.columns:
        df['result'] = df['result'].astype(str).str.upper().str.strip()
    if 'opponent' in df.columns:
        df['opponent'] = (
            df['opponent'].astype(str)
            .str.replace(r'\s+', ' ', regex=True)
            .str.strip()
        )
    if 'venue' in df.columns:
        df['venue'] = df['venue'].fillna('').astype(str).str.title()
    return df

def infer_venue_and_clean_opponent(row):
    opp = str(row.get('opponent','')).lstrip('= ').strip()
    ven = str(row.get('venue','')).strip()
    m = re.match(r'^(at|vs\.?)\s+(.*)$', opp, flags=re.I)
    if m:
        ven = ven or ('Away' if m.group(1).lower().startswith('at') else 'Home')
        opp = m.group(2)
    row['opponent'] = opp.title()
    row['venue'] = ven.title() if ven else ven
    return row

def clean_filter(df: pd.DataFrame, start=None, end=None) -> pd.DataFrame:
    df = normalize_columns(df)
    df = coerce_types(df)
    df = df.dropna(subset=['date'])
    if start: df = df[df['date'] >= pd.Timestamp(start)]
    if end:   df = df[df['date'] <= pd.Timestamp(end)]
    if 'result' in df.columns:
        df = df[df['result'].isin(['W','L'])]  # drop non-games
    df = df[(df['goals_for'].between(1,35)) & (df['goals_against'].between(1,35))]
    # opponent must contain letters (avoid stray numeric/OCR junk)
    df = df[df['opponent'].str.contains(r'[A-Za-z]', regex=True, na=False)]
    # derive venue tokens inside opponent if present
    df = df.apply(infer_venue_and_clean_opponent, axis=1)
    df = df.drop_duplicates(subset=['date','opponent','goals_for','goals_against','result'])
    return df.sort_values('date')

def flipped(df: pd.DataFrame, gf_delta=0, ga_delta=0) -> pd.DataFrame:
    a = df.copy()
    a['gf_adj'] = a['goals_for'] + gf_delta
    a['ga_adj'] = (a['goals_against'] - ga_delta).clip(lower=0)
    mask = (a['result']!='W') & (a['gf_adj'] > a['ga_adj'])
    return a.loc[mask, ['date','opponent','goals_for','goals_against']]

def best_split(df: pd.DataFrame, d: int):
    best = (0,0,0)  # flips, gf_delta, ga_delta
    for k in range(d+1):
        f = len(flipped(df, gf_delta=k, ga_delta=d-k))
        if f > best[0]:
            best = (f, k, d-k)
    return best

def main():
    ap = argparse.ArgumentParser(description="Clean season CSV and run goal-swing sensitivity")
    ap.add_argument("--inp", default=None, help="Input CSV (games.csv or games_clean.csv)")
    ap.add_argument("--outdir", default=".", help="Output directory")
    ap.add_argument("--season-start", default=None, help="YYYY-MM-DD")
    ap.add_argument("--season-end", default=None, help="YYYY-MM-DD")
    ap.add_argument("--dmax", type=int, default=4, help="Max total swing to test (default 4)")
    args = ap.parse_args()

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)

    # Pick sensible default input
    if args.inp:
        inp = Path(args.inp)
    else:
        # prefer games.csv in outdir, else games_clean.csv
        cand1 = outdir / "games.csv"
        cand2 = outdir / "games_clean.csv"
        inp = cand1 if cand1.exists() else cand2

    if not inp.exists():
        print(f"Input not found: {inp}")
        return

    df_raw = pd.read_csv(inp)
    df = clean_filter(df_raw, start=args.season_start, end=args.season_end)

    # Write cleaned + final
    clean_path = outdir / "games_clean.csv"
    final_path = outdir / "games_final.csv"
    df_out = df.copy()
    df_out['date'] = df_out['date'].dt.date.astype(str)
    df_out.to_csv(clean_path, index=False)
    df_out[['date','opponent','venue','result','goals_for','goals_against']].to_csv(final_path, index=False)

    # Basics
    wins = int((df['result']=='W').sum())
    losses = int((df['result']=='L').sum())
    print(f"Games: {len(df)}")
    print(f"Record: {wins} W — {losses} L")
    print(f"Avg GF: {df['goals_for'].mean():.2f}  Avg GA: {df['goals_against'].mean():.2f}")

    # Sensitivity table
    lines = []
    for d in range(1, args.dmax+1):
        off = len(flipped(df, gf_delta=d))
        dea = len(flipped(df, ga_delta=d))
        best_flips, gfd, gad = best_split(df, d)
        lines.append(f"d={d}: +{d}GF -> {off} flips | -{d}GA -> {dea} flips | best split +{gfd}GF/-{gad}GA -> {best_flips} flips")
    print("\n" + "\n".join(lines))

    # Detail lists for d=2 and d=4 (if within range)
    detail_txt = []
    for d in (2,4):
        if d <= args.dmax:
            f_off = flipped(df, gf_delta=d)
            f_def = flipped(df, ga_delta=d)
            detail_txt.append(f"\n=== Flips with +{d} GF ===\n{f_off.to_string(index=False) if not f_off.empty else '(none)'}")
            detail_txt.append(f"\n=== Flips with -{d} GA ===\n{f_def.to_string(index=False) if not f_def.empty else '(none)'}")
    summary_path = outdir / "flips_summary.txt"
    open(summary_path, "w").write("\n".join([*lines, *detail_txt]))
    print(f"\nWrote: {clean_path}")
    print(f"Wrote: {final_path}")
    print(f"Wrote: {summary_path}")

if __name__ == "__main__":
    main()
