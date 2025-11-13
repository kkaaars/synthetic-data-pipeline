import os, json, re, pandas as pd
from collections import defaultdict
from pathlib import Path

OUTPUT="output"
MAPPING=os.path.join(OUTPUT,"mapping_meta.csv")
META=os.path.join(OUTPUT,"meta.json")
with open("config.json","r",encoding="utf-8") as f:
    config=json.load(f)

# load sit regex map (raw patterns)
sit_patterns = {s["id"]: s.get("regex","") for s in config.get("sits",[])}

df = pd.read_csv(MAPPING, dtype=str)
df = df.fillna("")

def read_txt_like(path):
    if not path: return ""
    p = Path(path)
    if not p.exists():
        p2 = Path("output/files")/p.name
        if p2.exists():
            p = p2
    if not p.exists(): return ""
    ext = p.suffix.lower()
    try:
        if ext == ".txt":
            return p.read_text(encoding="utf-8",errors="ignore")
        # try simple docx
        if ext == ".docx":
            import docx
            d=docx.Document(str(p)); return "\n".join([pp.text for pp in d.paragraphs])
        if ext == ".pdf":
            import PyPDF2
            out=[]
            with open(p,"rb") as f:
                r=PyPDF2.PdfReader(f)
                for page in r.pages:
                    out.append(page.extract_text() or "")
            return "\n".join(out)
        if ext == ".eml":
            from email import policy
            from email.parser import BytesParser
            with open(p,"rb") as f:
                msg = BytesParser(policy=policy.default).parse(f)
            if msg.is_multipart():
                parts=[part.get_content() for part in msg.walk() if part.get_content_type()=="text/plain"]
                return "\n".join(parts)
            return msg.get_content()
    except Exception:
        return ""
    return ""

# collect where TP failed or FP flagged from your report we saved earlier: find rows where labels contain TP/FP etc.
samples = defaultdict(lambda: {"tp_total":0,"fp_total":0,"tp_fail_docs":[],"fp_flag_docs":[],"matches_sample":[]})

for _, row in df.iterrows():
    sit_ids = row.get("sit_ids","").split(";") if row.get("sit_ids") else []
    labels = row.get("labels","").split(";") if row.get("labels") else []
    path = row.get("actual_file_path") or row.get("docx_path") or row.get("pdf_path") or ""
    text = read_txt_like(path)
    for i,sid in enumerate(sit_ids):
        sid = sid.strip()
        lbl = labels[i] if i < len(labels) else "TP"
        pat = sit_patterns.get(sid,"")
        if not pat: continue
        try:
            regex = re.compile(pat, flags=re.IGNORECASE | re.MULTILINE)
            found = regex.findall(text) if text else []
        except re.error:
            found = []
        if lbl=="TP":
            if len(found)==0:
                if len(samples[sid]["tp_fail_docs"])<10:
                    samples[sid]["tp_fail_docs"].append((row.get("doc_id"), path))
                samples[sid]["tp_total"] += 1
            else:
                if len(samples[sid]["matches_sample"])<5:
                    samples[sid]["matches_sample"].extend(found[:5])
        else:
            if len(found)>0:
                if len(samples[sid]["fp_flag_docs"])<10:
                    samples[sid]["fp_flag_docs"].append((row.get("doc_id"), path, found[:5]))
                samples[sid]["fp_total"] += 1

# print summary for SITs with issues
for sid, info in samples.items():
    if info["tp_total"]>0 or info["fp_total"]>0:
        print("SIT:", sid)
        print("  TP missing count (sample docs up to 10):", len(info["tp_fail_docs"]))
        if info["tp_fail_docs"]:
            for d,p in info["tp_fail_docs"][:5]:
                print("    doc_id",d,"path",p)
        print("  FP flagged count (sample up to 10):", len(info["fp_flag_docs"]))
        if info["fp_flag_docs"]:
            for d,p,found in info["fp_flag_docs"][:5]:
                print("    doc_id",d,"path",p,"found_sample:",found)
        if info["matches_sample"]:
            print("  sample matches found elsewhere:", info["matches_sample"][:5])
        print("-"*60)
