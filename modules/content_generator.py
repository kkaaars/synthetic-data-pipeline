"""
content_generator.py

Reads:
 - config.json
 - output/meta.json

Generates .txt files (one per meta doc) into output/files/
Updates output/mapping_meta.csv adding columns actual_file_path and actual_word_count.

Deterministic when config.random_seed is set.
"""

import os
import json
import random
import string
from datetime import datetime
from faker import Faker
import pandas as pd

fake = Faker()

# -----------------------------
# Helpers: checksum/generators
# -----------------------------
def luhn_checksum_for(body_digits: str) -> int:
    def digits_of(n):
        return [int(d) for d in str(n)]
    digits = digits_of(body_digits)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    total = sum(odd_digits)
    for d in even_digits:
        total += sum(digits_of(d*2))
    return (10 - (total % 10)) % 10

def generate_ccn(tp=True):
    if not tp:
        return "0000 0000 0000 0000"
    prefix = random.choice(["4", random.choice([f"5{random.choice(range(1, 6))}", "51", "52", "53", "54", "55"])])
    length_without_check = 15
    body = prefix + "".join(random.choice(string.digits) for _ in range(length_without_check - len(prefix)))
    check = luhn_checksum_for(body)
    full = body + str(check)
    parts = [full[i:i+4] for i in range(0, len(full), 4)]
    return " ".join(parts)


def iban_replace_chars(s):
    out = ""
    for ch in s:
        if ch.isdigit():
            out += ch
        else:
            out += str(ord(ch.upper()) - 55)
    return out

def iban_calc_checksum(country_code, bban):
    rearranged = bban + country_code + "00"
    numeric = iban_replace_chars(rearranged)
    remainder = 0
    for i in range(0, len(numeric), 9):
        block = str(remainder) + numeric[i:i+9]
        remainder = int(block) % 97
    checksum = 98 - remainder
    return f"{checksum:02d}"

def generate_iban(tp=True, country_code="GB"):
    if not tp:
        return "XX00 XXXX XXXX XXXX XXXX"
    bban = "".join(random.choice(string.digits) for _ in range(16))
    checksum = iban_calc_checksum(country_code, bban)
    return f"{country_code}{checksum}{bban}"

def generate_ssn(tp=True):
    if not tp:
        return "XXX-XX-XXXX"
    part1 = random.randint(100, 899)
    part2 = random.randint(10, 99)
    part3 = random.randint(1000, 9999)
    return f"{part1:03d}-{part2:02d}-{part3:04d}"

def generate_ip(tp=True):
    if not tp:
        return "999.999.999.999"
    return fake.ipv4()

def generate_aba(tp=True):
    if not tp:
        return "000000000"
    return "".join(random.choice(string.digits) for _ in range(9))

def generate_dea(tp=True):
    if not tp:
        return "ZZ0000000"
    letters = "".join(random.choice(string.ascii_uppercase) for _ in range(2))
    digits = "".join(random.choice(string.digits) for _ in range(7))
    return letters + digits

def generate_passport(tp=True):
    if not tp:
        return "XXXXXXXX"
    return random.choice(string.ascii_uppercase) + "".join(random.choice(string.digits) for _ in range(7))

def generate_bank_account(tp=True, min_len=6, max_len=17):
    if not tp:
        return "0000000"
    length = random.randint(min_len, max_len)
    return "".join(random.choice(string.digits) for _ in range(length))

def generate_nino(tp=True):
    if not tp:
        return "QQ000000C"
    # exclude disallowed letters for first two positions (approx)
    allowed = [c for c in string.ascii_uppercase if c not in "DFIQUV"]
    l1 = random.choice(allowed)
    l2 = random.choice(allowed)
    digits = "".join(random.choice(string.digits) for _ in range(6))
    suffix = random.choice(list("ABCD"))
    return f"{l1}{l2}{digits}{suffix}"

def generate_cpf(tp=True):
    if not tp:
        return "000.000.000-00"
    p1 = "".join(random.choice(string.digits) for _ in range(3))
    p2 = "".join(random.choice(string.digits) for _ in range(3))
    p3 = "".join(random.choice(string.digits) for _ in range(3))
    p4 = "".join(random.choice(string.digits) for _ in range(2))
    return f"{p1}.{p2}.{p3}-{p4}"

# generic fallback
def gen_generic_placeholder(sit_name, tp, sit_id=None):
    if tp:
        return f"<{sit_name.replace(' ', '_').upper()}_VALUE>"
    if sit_id:
        return f"REDACTED_{sit_id}"
    return f"REDACTED_{sit_name.replace(' ', '_').upper()}"

# -----------------------------
# SIT generators map
# -----------------------------
SIT_GENERATORS = {
    "SIT_CCN": generate_ccn,
    "SIT_SSN": generate_ssn,
    "SIT_ITIN": generate_ssn,
    "SIT_PASSPORT_US_UK": generate_passport,
    "SIT_BANK_US": lambda tp: generate_bank_account(tp, 6, 17),
    "SIT_DRIVER_US": lambda tp: (fake.bothify(text='?######?') if tp else "XXXXXXX"),
    "SIT_ABA": generate_aba,
    "SIT_DEA": generate_dea,
    "SIT_EU_DEBIT": generate_ccn,
    "SIT_ICD10": lambda tp: (fake.lexify(text='A##') if tp else "X00"),
    "SIT_ICD9": lambda tp: (f"{random.randint(100,999)}.{random.randint(0,99)}" if tp else "000"),
    "SIT_SWIFT": lambda tp: (''.join(random.choice(string.ascii_uppercase) for _ in range(8)) if tp else "XXXXXX"),
    "SIT_CAN_SIN": lambda tp: (f"{random.randint(100,999)}-{random.randint(100,999)}-{random.randint(100,999)}" if tp else "000-000-000"),
    "SIT_CAN_BANK": lambda tp: generate_bank_account(tp, 7, 12),
    "SIT_AUS_TFN": lambda tp: (''.join(random.choice(string.digits) for _ in range(8)) if tp else "00000000"),
    "SIT_CAN_PHIN": lambda tp: (''.join(random.choice(string.digits) for _ in range(9)) if tp else "000000000"),
    "SIT_CAN_DRIVER": lambda tp: (fake.bothify(text='??######') if tp else "XXXXXX"),
    "SIT_CAN_HEALTH": lambda tp: (''.join(random.choice(string.digits) for _ in range(9)) if tp else "000000000"),
    "SIT_AUS_DRIVER": lambda tp: (fake.bothify(text='??-######') if tp else "XXXX-000000"),
    "SIT_AUS_PASSPORT": lambda tp: (random.choice(string.ascii_uppercase) + ''.join(random.choice(string.digits) for _ in range(7)) if tp else "A0000000"),
    "SIT_AUS_BANK": lambda tp: generate_bank_account(tp, 6, 9),
    "SIT_AZURE_SAS": lambda tp: ("sig=FAKE_SIG" if tp else "sig=XXXXX"),
    "SIT_CAN_PASSPORT": generate_passport,
    "SIT_AUS_MEDACC": lambda tp: generate_bank_account(tp, 6, 12),
    "SIT_IBAN": generate_iban,
    "SIT_BR_CPF": generate_cpf,
    "SIT_BR_RG": lambda tp: (f"{random.randint(10,99)}.{random.randint(100,999)}.{random.randint(100,999)}-{random.randint(0,9)}" if tp else "00.000.000-0"),
    "SIT_UK_NINO": generate_nino,
    "SIT_FR_INSEE": lambda tp: (''.join(random.choice(string.digits) for _ in range(13)) if tp else "0000000000000"),
    "SIT_IP": generate_ip
    # other SITs fall back to generic placeholder
}

# -----------------------------
# Templates
# -----------------------------
EMAIL_TEMPLATE = "From: {from_email}\nTo: {to_email}\nSubject: {subject}\n\n{body}\n\nRegards,\n{sender}\n"
CHAT_LINE_TEMPLATE = "[{time}] {user}: {message}"
DOC_HEADER_TEMPLATE = "{title}\n\n"

# -----------------------------
# Utilities
# -----------------------------
def ensure_folder(path):
    os.makedirs(path, exist_ok=True)

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def choose_generator(sit_id):
    return SIT_GENERATORS.get(sit_id, None)

def generate_sit_value(sit_id, sit_name, label):
    tp = (label == "TP")
    gen = choose_generator(sit_id)
    if gen:
        try:
            return gen(tp)
        except Exception:
            return gen_generic_placeholder(sit_name, tp, sit_id=sit_id)
    else:
        return gen_generic_placeholder(sit_name, tp, sit_id=sit_id)

def build_email_body(doc_meta):
    parts = []
    for s in doc_meta["sits"]:
        value = generate_sit_value(s["sit_id"], s["sit_name"], s["label"])
        parts.append(f"{s['sit_name']}: {value}\nContext: related to {', '.join(s.get('tcs', []))}.")
    body = "\n\n".join(parts)
    return body

def build_chat_text(doc_meta):
    lines = []
    for i, s in enumerate(doc_meta["sits"]):
        t = fake.time(pattern="%H:%M")
        user1 = fake.first_name()
        user2 = fake.first_name()
        val = generate_sit_value(s["sit_id"], s["sit_name"], s["label"])
        lines.append(CHAT_LINE_TEMPLATE.format(time=t, user=user1, message=f"Please share the {s['sit_name']}."))
        lines.append(CHAT_LINE_TEMPLATE.format(time=t, user=user2, message=f"The {s['sit_name']} is {val}."))
    return "\n".join(lines)

def build_document_text(doc_meta):
    title = f"CONFIDENTIAL - Document {doc_meta.get('doc_id')}"
    parts = [DOC_HEADER_TEMPLATE.format(title=title)]
    for s in doc_meta["sits"]:
        val = generate_sit_value(s["sit_id"], s["sit_name"], s["label"])
        parts.append(f"{s['sit_name']}: {val}\nDetails: related TCs: {', '.join(s.get('tcs', []))}.")
    parts.append(f"\nGenerated at: {datetime.utcnow().isoformat()}Z")
    return "\n\n".join(parts)

def fill_to_target(text, target_words):
    current = len(text.split())
    while current < target_words:
        p = fake.paragraph(nb_sentences=random.randint(2,6))
        text += "\n\n" + p
        current = len(text.split())
    return text

# -----------------------------
# Main
# -----------------------------
def main():
    ensure_folder("output/files")
    if not os.path.exists("config.json"):
        print("ERROR: config.json not found.")
        return
    if not os.path.exists("output/meta.json"):
        print("ERROR: output/meta.json not found. Run meta_generator.py first.")
        return

    config = load_json("config.json")
    meta = load_json("output/meta.json")
    docs = meta.get("docs", [])
    random_seed = config.get("random_seed", None)
    if random_seed is not None:
        random.seed(random_seed)
        Faker.seed(random_seed)

    # Load existing mapping CSV if present
    mapping_csv = "output/mapping_meta.csv"
    if os.path.exists(mapping_csv):
        df_map = pd.read_csv(mapping_csv, dtype=str)
    else:
        # create base df and we'll append rows
        df_map = pd.DataFrame(columns=["doc_id","filename","format","word_count_target","sit_ids","labels","instances","confidences","tcs"])

    # build index for quick update by doc_id
    existing_docids = set()
    if 'doc_id' in df_map.columns:
        for v in df_map['doc_id'].values:
            try:
                existing_docids.add(int(v))
            except Exception:
                pass

    updated_rows = []
    for idx, doc_meta in enumerate(docs, start=1):
        filename = doc_meta.get("filename")
        out_path = os.path.join("output/files", filename)
        fmt = doc_meta.get("format", "document")
        if fmt == "email":
            body = build_email_body(doc_meta)
            txt = EMAIL_TEMPLATE.format(from_email=fake.email(), to_email=fake.email(), subject=fake.sentence(nb_words=6), body=body, sender=fake.name())
        elif fmt == "chat":
            txt = build_chat_text(doc_meta)
        elif fmt in ("document", "pdf"):
            txt = build_document_text(doc_meta)
        elif fmt == "email_with_attachment":
            body = build_email_body(doc_meta)
            attachments_note = "\n\nAttached: report.xlsx"
            txt = EMAIL_TEMPLATE.format(from_email=fake.email(), to_email=fake.email(), subject=fake.sentence(nb_words=6), body=body + attachments_note, sender=fake.name())
        else:
            txt = build_document_text(doc_meta)

        # fill to word count target
        target = int(doc_meta.get("word_count_target", 500))
        txt = fill_to_target(txt, target)

        # write file
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(txt)

        word_count = len(txt.split())

        # prepare mapping row update
        sit_ids = ";".join([s["sit_id"] for s in doc_meta.get("sits", [])])
        labels = ";".join([s["label"] for s in doc_meta.get("sits", [])])
        instances = ";".join([str(s["instances"]) for s in doc_meta.get("sits", [])])
        confidences = ";".join([s["confidence"] for s in doc_meta.get("sits", [])])
        tcs = ";".join({tc for s in doc_meta.get("sits", []) for tc in s.get("tcs", [])})

        row = {
            "doc_id": doc_meta.get("doc_id"),
            "filename": filename,
            "format": fmt,
            "word_count_target": doc_meta.get("word_count_target"),
            "sit_ids": sit_ids,
            "labels": labels,
            "instances": instances,
            "confidences": confidences,
            "tcs": tcs,
            "actual_file_path": out_path,
            "actual_word_count": word_count
        }

        updated_rows.append(row)

        if idx % 100 == 0 or idx == len(docs):
            print(f"[{idx}/{len(docs)}] Generated {out_path} ({word_count} words)")

    # merge updated_rows into df_map (prefer existing columns)
    df_new = pd.DataFrame(updated_rows)
    if df_map.empty:
        df_final = df_new
    else:
        # try to align by doc_id: update rows that exist, append others
        df_map['doc_id'] = df_map['doc_id'].astype(str)
        df_new['doc_id'] = df_new['doc_id'].astype(str)
        df_map_indexed = df_map.set_index('doc_id', drop=False)
        for _, r in df_new.iterrows():
            did = r['doc_id']
            if did in df_map_indexed.index:
                for col in r.index:
                    df_map_indexed.at[did, col] = r[col]
            else:
                df_map_indexed = pd.concat([df_map_indexed, pd.DataFrame([r])], ignore_index=False)
        df_final = df_map_indexed.reset_index(drop=True)

    # save mapping csv (overwrite)
    df_final.to_csv("output/mapping_meta.csv", index=False)
    print("Generation complete. Files are in output/files/. mapping_meta.csv updated.")

if __name__ == "__main__":
    main()
