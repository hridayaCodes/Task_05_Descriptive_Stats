#!/usr/bin/env python3
import argparse, os, re, subprocess, sys, unicodedata, tempfile
from typing import List, Optional
import pandas as pd
from pdfminer.high_level import extract_text

MONTH = r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t|tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?"
RX_DATE_NUM  = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")
RX_DATE_NAME = re.compile(r"\b" + MONTH + r"\s+\d{1,2}(?:,\s*\d{4})?\b", re.IGNORECASE)
RX_RES       = re.compile(r"\b(W|L|T)\b", re.IGNORECASE)
RX_SCORE     = re.compile(r"(?<!\d)(\d{1,2})\s*-\s*(\d{1,2})(?!\s*[-/]\d)")

def clean(s: str) -> str:
    s = (s or "").replace("\xa0"," ").replace("\u2007"," ").replace("\u2009"," ")
    s = s.replace("–","-").replace("—","-").replace("\u2013","-").replace("\u2014","-")
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"\s+"," ", s).strip()

def parse_pages_arg(pages: Optional[str], total_pages: int) -> Optional[List[int]]:
    if not pages: return None
    idxs=set()
    for part in pages.split(","):
        part=part.strip()
        if "-" in part:
            a,b=part.split("-",1); a,b=int(a),int(b)
            for x in range(a,b+1): idxs.add(x-1)
        else:
            idxs.add(int(part)-1)
    return sorted(i for i in idxs if 0<=i<total_pages)

def ocr_if_needed(src_pdf: str, force: bool) -> str:
    if not force: return src_pdf
    out = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False).name
    cmd = ["ocrmypdf","--deskew","--clean","--force-ocr",src_pdf,out]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return out
    except FileNotFoundError:
        print("Warning: ocrmypdf not found; proceeding without OCR.", file=sys.stderr)
        return src_pdf
    except subprocess.CalledProcessError:
        print("Warning: ocrmypdf failed; proceeding without OCR.", file=sys.stderr)
        return src_pdf

def extract_pages_text(pdf_path: str, pages_arg: Optional[str]) -> List[str]:
    full_text = extract_text(pdf_path) or ""
    pages = [p for p in full_text.split("\f") if p.strip()]
    if not pages: return []
    if pages_arg:
        idxs = parse_pages_arg(pages_arg, len(pages))
        return [pages[i] for i in idxs]
    return pages

def parse_schedule_from_text(pages: List[str]) -> pd.DataFrame:
    rows=[]
    for pg_idx, pg in enumerate(pages,1):
        L=[clean(x) for x in pg.splitlines()]
        n=len(L)
        for i in range(n):
            for text in (L[i], (L[i]+" "+L[i+1]) if i+1<n else L[i]):
                if not text: continue
                m_res=RX_RES.search(text); m_sc=RX_SCORE.search(text)
                m_dn=RX_DATE_NUM.search(text); m_dm=RX_DATE_NAME.search(text)
                if not (m_res and m_sc and (m_dn or m_dm)): continue
                date_str=(m_dn.group(0) if m_dn else m_dm.group(0))
                date_end=(m_dn.end() if m_dn else m_dm.end())
                res=m_res.group(1).upper()
                gf,ga=int(m_sc.group(1)),int(m_sc.group(2))
                lo=" "+text.lower()+" "
                if " neutral " in lo: venue="Neutral"
                elif " at " in lo:    venue="Away"
                elif " vs " in lo:    venue="Home"
                else:
                    m_han=re.search(r"\b(H|A|N)\b",text)
                    venue={"H":"Home","A":"Away","N":"Neutral"}.get(m_han.group(1),"") if m_han else ""
                end_pos=min(m_res.start(), m_sc.start())
                opponent=text[date_end:end_pos]
                opponent=re.sub(r"^(at|vs\.?|neutral)\s+","",opponent,flags=re.IGNORECASE).strip(" -:|")
                if len(opponent)<2:
                    alpha=re.findall(r"[A-Za-z][A-Za-z0-9 .&'()/\-]{2,}",text)
                    opponent=max(alpha,key=len).strip() if alpha else ""
                rows.append({"page":pg_idx,"date_raw":date_str,"opponent":opponent,"venue":venue,
                             "result":res,"goals_for":gf,"goals_against":ga,"raw":text})
    return pd.DataFrame(rows).drop_duplicates()

def main():
    ap=argparse.ArgumentParser(description="OCR + parse season PDF into games.csv")
    ap.add_argument("pdf")
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--outfile", default="games.csv")
    ap.add_argument("--pages", default=None)
    ap.add_argument("--force-ocr", action="store_true")
    ap.add_argument("--season-start", default=None)
    ap.add_argument("--season-end", default=None)
    ap.add_argument("--dump-text", action="store_true")
    args=ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    pdf_for_parse=ocr_if_needed(args.pdf, args.force_ocr)

    pages_text=extract_pages_text(pdf_for_parse, args.pages)
    if not pages_text:
        print("No text extracted from PDF. Try --force-ocr.", file=sys.stderr); sys.exit(2)

    if args.dump_text:
        txt_dir=os.path.join(args.outdir,"pdf_text_dump"); os.makedirs(txt_dir, exist_ok=True)
        for i,pg in enumerate(pages_text,1):
            open(os.path.join(txt_dir,f"page{i:02d}.txt"),"w",encoding="utf-8").write(pg)

    df=parse_schedule_from_text(pages_text)
    if df.empty:
        print("Parsed 0 schedule rows. Try adjusting --pages or use --force-ocr.", file=sys.stderr); sys.exit(3)

    df["date"]=pd.to_datetime(df["date_raw"], errors="coerce")
    df=df.dropna(subset=["date"])
    if args.season_start: df=df[df["date"]>=pd.Timestamp(args.season_start)]
    if args.season_end:   df=df[df["date"]<=pd.Timestamp(args.season_end)]
    df=df[df["goals_for"].between(1,35) & df["goals_against"].between(1,35)]
    df=df[df["result"].isin(["W","L","T"])]

    df=df.sort_values("date")
    out=df[["date","opponent","venue","result","goals_for","goals_against","page","raw"]].copy()
    out["date"]=out["date"].dt.date.astype(str)

    out_path=os.path.join(args.outdir, args.outfile)
    out.to_csv(out_path, index=False)

    wins=int((out["result"]=="W").sum()); losses=int((out["result"]=="L").sum()); ties=int((out["result"]=="T").sum())
    print(f"Wrote {out_path} with {len(out)} rows")
    print(f"Record: {wins}-{losses}{('-'+str(ties)+' T') if ties else ''}")
    print(f"Avg GF: {out['goals_for'].mean():.2f}  Avg GA: {out['goals_against'].mean():.2f}")
if __name__=="__main__": main()
