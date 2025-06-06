import os
import spacy
from spacy.pipeline import EntityRuler
from spacy import displacy
from collections import defaultdict
from spacy.tokens import Doc
from typing import List, Dict
import json



# === CONFIG ===
INPUT_DIR = "raw_TXT"
OUTPUT_DIR = "html_TEST"
ENTITY_PATTERNS = [
    {"label": "SUM", "pattern": [{"TEXT": "Sumário"}, {"TEXT": ":", "OP": "!"}]},
    {"label": "TEXTO", "pattern": "Texto"},
    {"label": "DES", "pattern": [{"LOWER": "despacho"}, {"TEXT": "n.º", "OP": "?"}, {"LIKE_NUM": True}]},
    {
    "label": "HEADER_DATE",
    "pattern": [
        {"LIKE_NUM": True},                  # "2"
        {"IS_PUNCT": True, "TEXT": "-"}, # "-"
        {"IS_ALPHA": True, "LENGTH": 1},  # "S"
        {"IS_SPACE": True, "OP": "?"},          # optional space
        {"LIKE_NUM": True},                     # "28"
        {"LOWER": "de"},
        {"LOWER": {"IN": ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
                          "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]}},
        {"LOWER": "de"},
        {"LIKE_NUM": True}  # "2025"
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

def extract_text_between_labels(doc, start_label: str, end_label: str) -> str | None:
    """
    Extracts the text span between the first occurrence of two labeled entities.

    Parameters:
        doc (spacy.tokens.Doc): The processed spaCy document.
        start_label (str): The entity label that marks the start of the span.
        end_label (str): The entity label that marks the end of the span.

    Returns:
        str | None: The extracted text between the two entities (excluding them),
                    or None if either label is not found in the expected order.
    """
    start, end = None, None

    for ent in doc.ents:
        if ent.label_ == start_label and start is None:
            start = ent.end
        elif ent.label_ == end_label and start is not None:
            end = ent.start
            break

    if start is not None and end is not None:
        return doc[start:end].text.strip()

    return None

def extract_text_between_labels_including_start(doc, start_label: str, end_label: str) -> str | None:
    """
    Extracts the text span starting from the first occurrence of a labeled entity 
    (inclusive of the start entity) up to the next occurrence of another labeled entity.

    Parameters:
        doc (spacy.tokens.Doc): The processed spaCy document.
        start_label (str): The entity label that marks the start of the span (included).
        end_label (str): The entity label that marks the end of the span (excluded).

    Returns:
        str | None: The extracted text from the start label to just before the end label,
                    or None if either label is not found in the expected order.
    """
    start, end = None, None

    for ent in doc.ents:
        if ent.label_ == start_label and start is None:
            start = ent.start  # inclusive
        elif ent.label_ == end_label and start is not None:
            end = ent.start  # exclusive
            break

    if start is not None and end is not None:
        return doc[start:end].text.strip()

    return None

def extract_all_sections_from_label_to_same(doc, label: str) -> list[str]:
    """
    Extracts all text spans in a document that start with a given label and end before the next occurrence
    of the same label. Includes the start entity in each extracted span.

    Parameters:
        doc (spacy.tokens.Doc): The processed spaCy document.
        label (str): The entity label used as a delimiter for sections.

    Returns:
        list[str]: A list of text segments starting from each occurrence of the given label
                   up to just before the next one.
    """
    sections = []
    starts = [ent.start for ent in doc.ents if ent.label_ == label]

    for i in range(len(starts)):
        start = starts[i]
        end = starts[i + 1] if i + 1 < len(starts) else len(doc)
        span = doc[start:end].text.strip()
        sections.append(span)

    return sections

def group_sections_by_secretaria_with_despachos(doc: spacy.tokens.Doc, extracted_doc: spacy.tokens.Doc) -> dict:
    """
    Groups DES sections under each SECRETARIA label as nested dictionaries.

    Parameters:
        doc (spacy.tokens.Doc): The full SpaCy document.
        extracted_doc (spacy.tokens.Doc): The portion of the doc between SUM and HEADER_DATE.

    Returns:
        dict: {
            "SECRETARIA NAME": {
                "DESPACHO LABEL": "Content of the section following it",
                ...
            },
            ...
        }
    """
    secretaria_dict = {}
    secretarias = [ent for ent in extracted_doc.ents if ent.label_ == "SECRETARIA"]
    des_ents = [ent for ent in extracted_doc.ents if ent.label_ == "DES"]

    for i, secretaria in enumerate(secretarias):
        start = secretaria.start
        end = secretarias[i + 1].start if i + 1 < len(secretarias) else len(extracted_doc)

        section_span = extracted_doc[start:end]
        section_despachos = [ent for ent in des_ents if start <= ent.start < end]

        des_dict = {}
        for j, des_ent in enumerate(section_despachos):
            des_start = des_ent.start
            des_end = (
                section_despachos[j + 1].start if j + 1 < len(section_despachos) else end
            )
            des_span = extracted_doc[des_start:des_end]
            des_title = des_ent.text.strip()
            des_content = extracted_doc[des_ent.end:des_end].text.strip()
            des_dict[des_title] = des_content

        secretaria_dict[secretaria.text.strip()] = des_dict

    return secretaria_dict


def save_secretaria_dict_to_json(secretaria_dict, txt_filename, output_dir):
    """
    Saves the secretaria dictionary to a JSON file named after the original .txt file.

    Parameters:
        secretaria_dict (dict): Dictionary where each key is a SECRETARIA and
                                values are dictionaries of DES labels and their content.
        txt_filename (str): The original .txt filename (e.g., "IISerie-095-2025-05-28Supl.txt").
        output_dir (str): Directory where the JSON file should be saved.
    """
    os.makedirs(output_dir, exist_ok=True)

    json_filename = os.path.splitext(txt_filename)[0] + ".json"
    json_path = os.path.join(output_dir, json_filename)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(secretaria_dict, f, ensure_ascii=False, indent=2)

    print(f"✅ JSON saved to: {json_path}")


# === Setup ===
os.makedirs(OUTPUT_DIR, exist_ok=True)

nlp = spacy.load("pt_core_news_lg")
ruler = nlp.add_pipe("entity_ruler", before="ner")
ruler.add_patterns(ENTITY_PATTERNS)

# === Process and Save HTML ===
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

#-----------------------------------------------------------------------------------------
    html = displacy.render(
        doc,
        style="ent",
        options={
            "ents": ["SUM", "TEXTO", "DES", "HEADER_DATE", "SECRETARIA"],
            "colors": {
                "SUM": "#ff6f61",       # soft red
                "TEXTO": "#6a9fb5",     # soft blue
                "DES": "#88c057",        # soft green
                "HEADER_DATE": "#88c555"       
            }
        },
        page=True
    )


    output_path = os.path.join(OUTPUT_DIR, f"{os.path.splitext(filename)[0]}.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ HTML saved to: {output_path}")
#------------------------------------------------------------------------------------------
"""
#------------------------------------------------------------------------------------------
extracted = extract_text_between_labels(doc, "SUM", "HEADER_DATE")
if extracted:
    print(f"\n--- Extracted Text from {filename} ---\n{extracted}\n")
else:
    print(f"⚠️ Couldn't find both SUM and HEADER_DATE in: {filename}")
#--------------------------------------------------------------------------------------------
# Reprocess the extracted text
extracted_doc = nlp(extracted)

des_sections = extract_all_sections_from_label_to_same(extracted_doc, "DES")

if des_sections:
    for i, section in enumerate(des_sections, 1):
        print(f"\n--- DES Section {i} ---\n{section}\n")
else:
    print("⚠️ No DES sections found.")
#-------------------------------------------------------------------------------------------
"""
extracted = extract_text_between_labels(doc, "SUM", "HEADER_DATE")
extracted_doc = nlp(extracted)

secretaria_dict = group_sections_by_secretaria_with_despachos(doc, extracted_doc)

save_secretaria_dict_to_json(secretaria_dict, filename, output_dir="json_exports")


