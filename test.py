import pandas as pd
df = pd.read_csv("output/mapping_meta.csv")

df['sit_count'] = df['sit_ids'].str.split(';').map(len)
print("Average number of SITs per document:", df['sit_count'].mean())

print(df['sit_count'].value_counts().sort_index())

all_labels = ";".join(df['labels']).split(";")
tp = all_labels.count("TP")
fp = all_labels.count("FP")
print(f"TP: {tp}, FP: {fp}, ratio TP/FP = {tp/fp:.2f}")
