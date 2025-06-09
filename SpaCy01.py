import os
import spacy
from spacy.pipeline import EntityRuler
import json

from clean_people_chunk import extract_people_from_chunk

# === CONFIG ===
INPUT_DIR = "raw_TXT"
OUTPUT_DIR = "json_exports"

# === Custom Entity Patterns ===
ENTITY_PATTERNS = [
    {"label": "SUM", "pattern": [{"TEXT": "Sumário"}, {"TEXT": ":", "OP": "!"}]},
    {"label": "TEXTO", "pattern": "Texto"},
    {"label": "DES", "pattern": [{"LOWER": "despacho"}, {"TEXT": "n.º", "OP": "?"}, {"LIKE_NUM": True}]},
    {
        "label": "HEADER_DATE",
        "pattern": [
            {"LIKE_NUM": True},
            {"IS_PUNCT": True, "TEXT": "-"},
            {"IS_ALPHA": True, "LENGTH": 1},
            {"IS_SPACE": True, "OP": "?"},
            {"LIKE_NUM": True},
            {"LOWER": "de"},
            {"LOWER": {"IN": [
                "janeiro", "fevereiro", "março", "abril", "maio", "junho",
                "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
            ]}},
            {"LOWER": "de"},
            {"LIKE_NUM": True}
        ]
    },
    {
        "label": "SECRETARIA",
        "pattern": [
            {"TEXT": {"REGEX": "^SECRETARIA(S)?$"}},
            {"IS_UPPER": True, "OP": "+"}
        ]
    }
]

# === Helper Functions ===

def extract_metadata_from_chunk(chunk: str, autor_mode=True):
    people = extract_people_from_chunk(chunk)
    return {
        "autor": people if autor_mode else [],
        "pessoas": [] if autor_mode else people
    }

def extract_text_between_labels(doc, start_label: str, end_label: str) -> str | None:
    start, end = None, None
    for ent in doc.ents:
        if ent.label_ == start_label and start is None:
            start = ent.end
        elif ent.label_ == end_label and start is not None:
            end = ent.start
            break
    return doc[start:end].text.strip() if start is not None and end is not None else None

def group_sections_by_secretaria_with_metadata(extracted_doc) -> dict:
    result = {}
    current_secretaria = None
    current_sections = []

    des_ents = [ent for ent in extracted_doc.ents if ent.label_ == "DES"]
    secretaria_ents = [ent for ent in extracted_doc.ents if ent.label_ == "SECRETARIA"]

    all_ents = sorted(secretaria_ents + des_ents, key=lambda x: x.start)

    for i, ent in enumerate(all_ents):
        if ent.label_ == "SECRETARIA":
            if current_secretaria and current_sections:
                result[current_secretaria] = {
                    sec["title"]: {
                        "chunk": sec["text"],
                        "data": "",
                        "autor": extract_metadata_from_chunk(sec["text"], autor_mode=True)["autor"],
                        "pessoas": [],
                        "despachos": "",
                        "serie": "",
                        "secretaria":"",
                    }
                    for sec in current_sections
                }
            current_secretaria = ent.text
            current_sections = []

        elif ent.label_ == "DES" and current_secretaria:
            start = ent.start
            end = all_ents[i + 1].start if i + 1 < len(all_ents) else len(extracted_doc)
            span = extracted_doc[start:end]
            current_sections.append({
                "title": ent.text,
                "text": span.text.replace(current_secretaria, "").strip()
            })

    if current_secretaria and current_sections:
        result[current_secretaria] = {
            sec["title"]: {
                "chunk": sec["text"],
                "data": "",
                "autor": extract_metadata_from_chunk(sec["text"], autor_mode=True)["autor"],
                "pessoas": [],
                "despachos": "",
                "serie": "",
                "secretaria":"",
            }
            for sec in current_sections
        }

    return result

def save_secretaria_dict_to_json(secretaria_dict, txt_filename, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    json_filename = os.path.splitext(txt_filename)[0] + ".json"
    json_path = os.path.join(output_dir, json_filename)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(secretaria_dict, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON saved to: {json_path}")

# === Setup NLP ===
nlp = spacy.load("pt_core_news_lg")
ruler = nlp.add_pipe("entity_ruler", before="ner")
ruler.add_patterns(ENTITY_PATTERNS)

# === Process All TXT Files ===
for filename in os.listdir(INPUT_DIR):
    if not filename.endswith(".txt"):
        continue

    filepath = os.path.join(INPUT_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    doc = nlp(text)

    if not any(ent.label_ in {"SUM", "TEXTO", "DES", "HEADER_DATE", "SECRETARIA"} for ent in doc.ents):
        print(f"❌ No custom entities in: {filename}")
        continue

    extracted = extract_text_between_labels(doc, "SUM", "HEADER_DATE")
    if not extracted:
        print(f"⚠️ Could not extract between SUM and HEADER_DATE in: {filename}")
        continue

    extracted_doc = nlp(extracted)
    secretaria_dict = group_sections_by_secretaria_with_metadata(extracted_doc)

    # Add "pessoas" from chunks (second-level metadata)
    for secretaria in secretaria_dict.values():
        for section in secretaria.values():
            pessoas = extract_metadata_from_chunk(section["chunk"], autor_mode=False)["pessoas"]
            section["pessoas"] = list(set(pessoas))  # optional deduplication

    save_secretaria_dict_to_json(secretaria_dict, filename, output_dir=OUTPUT_DIR)
