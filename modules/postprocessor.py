import os
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from email.message import EmailMessage
from email.utils import formatdate
import mimetypes
import logging

# docx generation
from docx import Document
# pdf generation
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# Logging setup
os.makedirs("output", exist_ok=True)
LOG_PATH = "output/postprocess.log"
logging.basicConfig(filename=LOG_PATH, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

OUT_FOLDER = Path("output/files")
OUT_FOLDER.mkdir(parents=True, exist_ok=True)

META_JSON = "output/meta.json"
MAPPING_CSV = "output/mapping_meta.csv"
MAPPING_FINAL_XLSX = "output/mapping_final.xlsx"

def load_meta():
    if not Path(META_JSON).exists():
        raise FileNotFoundError(f"{META_JSON} not found. Run meta_generator first.")
    with open(META_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

def read_mapping_csv():
    if not Path(MAPPING_CSV).exists():
        raise FileNotFoundError(f"{MAPPING_CSV} not found. Run content_generator first.")
    return pd.read_csv(MAPPING_CSV, dtype=str)

def save_mapping_csv(df):
    df.to_csv(MAPPING_CSV, index=False)

def write_docx(text, out_path):
    doc = Document()
    for para in text.split("\n\n"):
        doc.add_paragraph(para)
    doc.save(out_path)

def write_pdf(text, out_path):
    c = canvas.Canvas(str(out_path), pagesize=A4)
    width, height = A4
    margin = 50
    y = height - margin
    c.setFont("Helvetica", 10)
    # break text into paragraphs and wrap lines ~100 chars
    lines = []
    for paragraph in text.split("\n\n"):
        words = paragraph.split()
        line = ""
        for w in words:
            if len(line) + 1 + len(w) > 100:
                lines.append(line)
                line = w
            else:
                line = (line + " " + w).strip() if line else w
        if line:
            lines.append(line)
        lines.append("")  # blank line
    for line in lines:
        if y < margin + 20:
            c.showPage()
            c.setFont("Helvetica", 10)
            y = height - margin
        # draw and move
        c.drawString(margin, y, line[:200])
        y -= 12
    c.save()

def create_xlsx_attachment(doc_meta, out_path):
    rows = []
    for s in doc_meta.get("sits", []):
        rows.append({
            "sit_id": s.get("sit_id"),
            "sit_name": s.get("sit_name"),
            "label": s.get("label"),
            "instances": s.get("instances"),
            "confidence": s.get("confidence"),
            "tcs": ",".join(s.get("tcs", []))
        })
    df = pd.DataFrame(rows)
    df.to_excel(out_path, index=False)

def attach_file_to_email(msg, filepath):
    ctype, encoding = mimetypes.guess_type(filepath)
    if ctype is None:
        ctype = 'application/octet-stream'
    maintype, subtype = ctype.split('/', 1)
    with open(filepath, 'rb') as f:
        data = f.read()
    msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=Path(filepath).name)

def create_eml(subject, from_addr, to_addr, body_text, attachments, out_path):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_addr
    msg['Date'] = formatdate(localtime=True)
    msg.set_content(body_text)
    for a in attachments:
        try:
            attach_file_to_email(msg, a)
        except Exception as e:
            logging.warning(f"Failed to attach {a}: {e}")
    with open(out_path, "wb") as f:
        f.write(bytes(msg))

def process_row(row, meta_map):
    out = {}
    try:
        doc_id = int(row.get("doc_id"))
    except Exception:
        logging.warning("Skipping row without valid doc_id")
        return out

    doc_meta = meta_map.get(doc_id)
    if not doc_meta:
        logging.warning(f"No meta found for doc_id {doc_id}")
        return out

    filename = doc_meta.get("filename")
    txt_path = OUT_FOLDER / filename
    if not txt_path.exists():
        logging.warning(f"TXT not found: {txt_path}")
        return out

    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    stem = Path(filename).stem
    # DOCX
    docx_name = f"{stem}.docx"
    docx_path = OUT_FOLDER / docx_name
    try:
        write_docx(text, docx_path)
        out["docx_path"] = str(docx_path)
    except Exception as e:
        logging.exception(f"Failed to write docx for {filename}: {e}")

    # PDF
    pdf_name = f"{stem}.pdf"
    pdf_path = OUT_FOLDER / pdf_name
    try:
        write_pdf(text, pdf_path)
        out["pdf_path"] = str(pdf_path)
    except Exception as e:
        logging.exception(f"Failed to write pdf for {filename}: {e}")

    attachments = []
    fmt = doc_meta.get("format", "document")
    if fmt in ("email", "email_with_attachment"):
        if fmt == "email_with_attachment":
            xlsx_name = f"{stem}_attachment.xlsx"
            xlsx_path = OUT_FOLDER / xlsx_name
            try:
                create_xlsx_attachment(doc_meta, xlsx_path)
                attachments.append(str(xlsx_path))
            except Exception as e:
                logging.exception(f"Failed to create xlsx attachment for {filename}: {e}")

        eml_name = f"{stem}.eml"
        eml_path = OUT_FOLDER / eml_name

        # Attempt to extract Subject / From / To from the .txt; fallback to generated
        subject = f"Automated message {stem}"
        from_addr = "no-reply@example.com"
        to_addr = "recipient@example.com"
        for line in text.splitlines():
            if line.lower().startswith("subject:"):
                subject = line.split(":",1)[1].strip()
            if line.lower().startswith("from:"):
                from_addr = line.split(":",1)[1].strip()
            if line.lower().startswith("to:"):
                to_addr = line.split(":",1)[1].strip()

        try:
            create_eml(subject, from_addr, to_addr, text, attachments, eml_path)
            out["eml_path"] = str(eml_path)
        except Exception as e:
            logging.exception(f"Failed to create eml for {filename}: {e}")

    out["attachments"] = ";".join(attachments) if attachments else ""
    out["postprocessed_at"] = datetime.utcnow().isoformat() + "Z"
    logging.info(f"Processed doc_id {doc_id}: docx={out.get('docx_path')} pdf={out.get('pdf_path')} eml={out.get('eml_path')} attach={out.get('attachments')}")
    return out

def main():
    logging.info("Postprocessor started.")
    meta = load_meta()
    docs = meta.get("docs", [])
    meta_map = {int(d["doc_id"]): d for d in docs}

    df = read_mapping_csv()

    # Ensure doc_id column is integer typed where possible
    if 'doc_id' in df.columns:
        try:
            df['doc_id'] = df['doc_id'].astype(int)
        except Exception:
            pass

    # Add columns if missing
    for col in ["docx_path", "pdf_path", "eml_path", "attachments", "postprocessed_at"]:
        if col not in df.columns:
            df[col] = ""

    # Process rows
    for idx, row in df.iterrows():
        try:
            updates = process_row(row, meta_map)
            for k, v in updates.items():
                df.at[idx, k] = v
        except Exception as e:
            logging.exception(f"Failed processing row idx {idx}: {e}")

    # Save updated CSV and final Excel
    save_mapping_csv(df)
    try:
        df.to_excel(MAPPING_FINAL_XLSX, index=False)
        logging.info(f"Saved final mapping to {MAPPING_FINAL_XLSX}")
    except Exception as e:
        logging.exception(f"Failed to write mapping_final.xlsx: {e}")

    logging.info("Postprocessor finished.")
    print("Postprocessing complete. See output/mapping_final.xlsx and output/postprocess.log")

if __name__ == "__main__":
    main()
