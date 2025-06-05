import spacy
import os

# === Config ===
NLP_MODEL = "pt_core_news_lg"
INPUT_DIR = "raw_TXT"
OUTPUT_DIR = "ner_HTML"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "all_results.html")

TRIM_KEYWORDS = ["anexo", "nota curricular", "secretaria"]

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load spaCy Portuguese model
nlp = spacy.load(NLP_MODEL)

def remove_single_word_entities(entities):
    return [e for e in entities if len(e.split()) > 1]

def trim_after_keywords(text, keywords):
    """
    Trims the text at the first occurrence of any keyword.
    """
    text_lower = text.lower()
    cut_index = len(text)

    for kw in keywords:
        index = text_lower.find(kw.lower())
        if index != -1 and index < cut_index:
            cut_index = index

    return text[:cut_index].strip()

def normalize_and_deduplicate(entities):
    """Normalize whitespace and remove duplicates from a list of strings."""
    normalized = [" ".join(e.split()) for e in entities]  # collapse whitespace
    return sorted(set(normalized), key=len)

def keep_shortest_prefix_entities(entities):
    """Remove entities that are longer extensions of another entity."""
    sorted_entities = sorted(set(entities), key=lambda x: (len(x.split()), x))
    result = []

    for ent in sorted_entities:
        ent_tokens = ent.split()
        is_extension = False

        for kept in result:
            kept_tokens = kept.split()
            if ent_tokens[:len(kept_tokens)] == kept_tokens:
                is_extension = True
                break

        if not is_extension:
            result.append(ent)

    return result




# Start HTML file
with open(OUTPUT_FILE, "w", encoding="utf-8") as html_file:
    html_file.write("<html><head><meta charset='utf-8'><title>PER Entities</title></head><body>\n")

    # Process each .txt file
    for filename in os.listdir(INPUT_DIR):
        if filename.endswith(".txt"):
            path = os.path.join(INPUT_DIR, filename)
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()

            doc = nlp(text)
            person_entities = [ent.text.strip() for ent in doc.ents if ent.label_ == "PER"]
            person_entities = remove_single_word_entities(person_entities)
            person_entities = [trim_after_keywords(p, TRIM_KEYWORDS) for p in person_entities]
            person_entities = keep_shortest_prefix_entities(person_entities)
            person_entities = normalize_and_deduplicate(person_entities)
            

            # Write to HTML
            html_file.write(f"<h2>{filename}</h2>\n<ul>\n")
            if person_entities:
                for person in person_entities:
                    html_file.write(f"<li>{person}</li>\n")
            else:
                html_file.write("<li>Nenhuma entidade 'PER' encontrada.</li>\n")
            html_file.write("</ul>\n<hr>\n")

    html_file.write("</body></html>")
