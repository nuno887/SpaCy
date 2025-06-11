
import os
import spacy
from spacy.pipeline import EntityRuler
import json
from spacy import displacy
from datetime import datetime

from clean_people_chunk import extract_people_from_chunk

INPUT_DIR_TXT = "raw_TXT_deleted"
OUTPUT_DIR_JSON = "raw_json_exports"
INPUT_DIR_JSON = "json_exports"

PRIMARY_PATTERNS = [
    {
        "label": "DES",
        "pattern": [
            {"LOWER": {"IN": ["despacho", "aviso", "edital", "deliberação", "portaria"]}},
            {"LOWER": {"IN": ["conjunto"]}, "OP": "?"},
            {"TEXT": "n.º", "OP": "?"},
            {"LIKE_NUM": True}
        
        ]
    },
    {
    "label": "DES",
    "pattern": [
        {"LOWER": "declaração"},
        {"LOWER": "de"},
        {"LOWER": "retificação"},
        {"TEXT": "n.º", "OP": "?"},  # Optional "n.º"
        {"LIKE_NUM": True},          # The number part, e.g., "16"
        {"TEXT": "/", "OP": "?"},    # Optional slash
        {"LIKE_NUM": True}           # The year part, e.g., "2025"
    ]
}

]

# === Setup NLP ===
nlp = spacy.load("pt_core_news_lg")

# Add composed/override patterns first
ruler_composed = nlp.add_pipe("entity_ruler", name="ruler_composed", before="ner")
ruler_composed.add_patterns(PRIMARY_PATTERNS)

def extract_text_between_labels(doc, start_label: str, end_label: str) -> str | None:
    start, end = None, None
    for ent in doc.ents:
        if ent.label_ == start_label and start is None:
            start = ent.end
        elif ent.label_ == end_label and start is not None:
            end = ent.start
            break
    return doc[start:end].text.strip() if start is not None and end is not None else None


def extract_valid_des_sections_between_valids(input_txt_dir: str, input_json_dir: str, output_json_dir: str) -> None:
    os.makedirs(output_json_dir, exist_ok=True)

    for filename in os.listdir(input_txt_dir):
        if not filename.endswith(".txt"):
            continue

        txt_path = os.path.join(input_txt_dir, filename)
        json_input_path = os.path.join(input_json_dir, filename.replace(".txt", ".json"))

        if not os.path.exists(json_input_path):
            print(f"Skipping {filename} — no matching JSON in {input_json_dir}")
            continue

        # Load valid DES titles
        with open(json_input_path, "r", encoding="utf-8") as jf:
            json_data = json.load(jf)

        valid_des_titles = {
            des_title
            for secretaria in json_data.values()
            for des_title in secretaria.keys()
        }

        # Process text
        with open(txt_path, "r", encoding="utf-8") as tf:
            text = tf.read()
        doc = nlp(text)

        # Filter valid DES entities (in order)
        des_ents = [
            ent for ent in doc.ents
            if ent.label_ == "DES" and ent.text.strip() in valid_des_titles
        ]

        sections = {}
        for i in range(len(des_ents) - 1):
            ent = des_ents[i]
            next_ent = des_ents[i + 1]

            title = ent.text.strip()
            start = ent.end
            end = next_ent.start
            content = doc[start:end].text.strip()

            sections[title] = {
                "text": content,
                "order": i + 1,
                "file_date": datetime.fromtimestamp(os.path.getmtime(txt_path)).isoformat(),
                "original_filename": filename
            }

     
        if des_ents:
            last_ent = des_ents[-1]
            title = last_ent.text.strip()
            content = doc[last_ent.end:].text.strip()
            sections[title] = {
                "text": content,
                "order": len(des_ents),
                "file_date": datetime.fromtimestamp(os.path.getmtime(txt_path)).isoformat(),
                "original_filename": filename
           }

        if sections:
            output_path = os.path.join(output_json_dir, filename.replace(".txt", ".json"))
            with open(output_path, "w", encoding="utf-8") as out_f:
                json.dump(sections, out_f, ensure_ascii=False, indent=2)
            
            # ✅ Generate HTML here — inside the loop
        html_output_dir = "raw_html_exports"
        os.makedirs(html_output_dir, exist_ok=True)
        html_output_path = os.path.join(html_output_dir, filename.replace(".txt", ".html"))

        html_content = f"<html><head><meta charset='UTF-8'><title>{filename}</title></head><body>"
        html_content += f"<h1>Sections from: {filename}</h1>"

        for title, data in sections.items():
            html_content += f"<hr><h2>{title}</h2>"
            html_content += f"<p><strong>Order:</strong> {data['order']}</p>"
            html_content += f"<p><strong>File Date:</strong> {data['file_date']}</p>"
            html_content += f"<p><strong>Original Filename:</strong> {data['original_filename']}</p>"
            html_content += f"<pre style='background:#f4f4f4;padding:10px;border:1px solid #ccc;'>{data['text']}</pre>"

        html_content += "</body></html>"

        with open(html_output_path, "w", encoding="utf-8") as html_file:
            html_file.write(html_content)



extract_valid_des_sections_between_valids(INPUT_DIR_TXT, INPUT_DIR_JSON, OUTPUT_DIR_JSON)


