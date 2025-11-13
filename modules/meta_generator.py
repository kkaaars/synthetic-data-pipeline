import json
import random
import os
import csv
from collections import defaultdict
from datetime import datetime
from itertools import cycle

def sample_from_bucket(dist_map):
    r = random.random()
    cum = 0.0
    for k, p in dist_map.items():
        cum += p
        if r <= cum:
            return k
    # fallback
    return list(dist_map.keys())[-1]

def parse_sit_count_bucket(bucket):
    if bucket == "1":
        return 1
    if bucket == "2-3":
        return random.randint(2,3)
    if bucket == "4-6":
        return random.randint(4,6)
    if bucket == ">6":
        return random.randint(7,10)
    # default
    return 1

def parse_instance_bucket(bucket):
    if bucket == "1":
        return 1
    if bucket == "3-5":
        return random.randint(3,5)
    if bucket == "6-10":
        return random.randint(6,10)
    if bucket == ">10":
        return random.randint(11,20)
    return 1

def assign_confidence(rules, label, instances):
    # simple evaluation using config rules
    if label == "TP":
        if instances >= rules['high']['min_instances']:
            return "High"
        if 3 <= instances <= 5:
            return "Medium"
        return "Low"
    else:  # FP
        if instances >= 3:
            return "Medium"
        return "Low"

def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def ensure_folder(path):
    os.makedirs(path, exist_ok=True)

def main(config_path="config.json", out_meta="output/meta.json", out_csv="output/mapping_meta.csv"):
    config = load_config(config_path)
    random.seed(config.get("random_seed", 42))
    ensure_folder("output")
    sits = config["sits"]
    sit_by_id = {s['id']: s for s in sits}

    # target counts per sit
    per_sit_target = config.get("per_sit_count", 100)

    # we'll count number of documents that include each sit
    sit_doc_counts = defaultdict(int)

    # we'll also track total instances across all docs (optional)
    sit_instance_counts = defaultdict(int)

    # list of sit ids to ensure coverage; we will iterate and try to cover each until target reached
    sit_ids_cycle = list(sit_by_id.keys())

    docs = []
    doc_id = 0

    # to avoid infinite loops, set a generous max docs
    max_docs = int(len(sit_ids_cycle) * per_sit_target * 2.5)

    while True:
        # stop condition
        all_ok = all(count >= per_sit_target for count in sit_doc_counts.values()) and len(sit_doc_counts) > 0
        if all_ok or doc_id >= max_docs:
            break

        doc_id += 1
        # choose format
        fmt = random.choice(config.get("formats", ["document"]))
        # choose number of different SITs in this doc
        bucket = sample_from_bucket(config["sit_count_distribution"])
        n_sits = parse_sit_count_bucket(bucket)

        # pick sits: prefer those with lower counts
        needed = [sid for sid, c in sit_doc_counts.items() if c < per_sit_target]
        # if some sits not yet present in counts dict, they are needed too
        missing = [sid for sid in sit_by_id.keys() if sid not in sit_doc_counts or sit_doc_counts[sid] < per_sit_target]
        # build candidate list sorted by ascending counts
        candidates = sorted(list(sit_by_id.keys()), key=lambda x: sit_doc_counts.get(x, 0))
        # pick n_sits from candidates
        chosen = []
        for sid in candidates:
            if len(chosen) >= n_sits:
                break
            if sid not in chosen:
                chosen.append(sid)
        # now for each chosen sit assign label TP/FP and instances and confidence
        sits_meta = []
        for sid in chosen:
            label = "TP" if random.random() < config.get("tp_ratio", 0.5) else "FP"
            inst_bucket = sample_from_bucket(config["instance_count_distribution"])
            instances = parse_instance_bucket(inst_bucket)
            confidence = assign_confidence(config["confidence_rules"], label, instances)
            sits_meta.append({
                "sit_id": sid,
                "sit_name": sit_by_id[sid]["name"],
                "label": label,
                "instances": instances,
                "confidence": confidence,
                "tcs": sit_by_id[sid].get("tc", [])
            })

        # choose target word count
        if random.random() < config["size_distribution"].get("main_range_share", 0.65):
            wc = random.randint(config["size_distribution"]["main_range_min"], config["size_distribution"]["main_range_max"])
        else:
            wc = random.randint(config["size_distribution"]["min_words"], config["size_distribution"]["max_words"])

        filename = f"doc_{doc_id:05d}_{fmt}.txt"

        doc_meta = {
            "doc_id": doc_id,
            "filename": filename,
            "format": fmt,
            "word_count_target": wc,
            "sits": sits_meta,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        docs.append(doc_meta)

        # update counts: we count that this document contains the SIT (one doc counts as one)
        for s in sits_meta:
            sit_doc_counts[s["sit_id"]] += 1
            sit_instance_counts[s["sit_id"]] += s["instances"]

    # save meta
    with open(out_meta, "w", encoding="utf-8") as f:
        json.dump({"generated_at": datetime.utcnow().isoformat() + "Z", "docs": docs, "sit_doc_counts": sit_doc_counts, "sit_instance_counts": sit_instance_counts}, f, indent=2, ensure_ascii=False)

    # write a CSV summary (one row per document)
    with open(out_csv, "w", encoding="utf-8", newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["doc_id","filename","format","word_count_target","sit_ids","labels","instances","confidences","tcs"])
        for d in docs:
            sit_ids = ";".join([s["sit_id"] for s in d["sits"]])
            labels = ";".join([s["label"] for s in d["sits"]])
            instances = ";".join([str(s["instances"]) for s in d["sits"]])
            confidences = ";".join([s["confidence"] for s in d["sits"]])
            tcs = ";".join({tc for s in d["sits"] for tc in s["tcs"]})
            writer.writerow([d["doc_id"], d["filename"], d["format"], d["word_count_target"], sit_ids, labels, instances, confidences, tcs])

    print(f"Meta generation done. Docs generated: {len(docs)}. Meta saved to {out_meta} and {out_csv}.")

if __name__ == "__main__":
    main()
