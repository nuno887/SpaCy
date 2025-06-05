import spacy
from spacy.matcher import Matcher
import os

# === Config ===
NLP_MODEL = "pt_core_news_lg"
INPUT_DIR = "raw_TXT"
HTML_DIR = "ner_HTML"

os.makedirs(HTML_DIR, exist_ok=True)

# === Load spaCy Portuguese model ===
nlp = spacy.load(NLP_MODEL)
matcher = Matcher(nlp.vocab)

UNWANTED_KEYWORDS = [
    "inspetor", "divisão", "diretor",
    "serviços", "autoridade", "assuntos fiscais", "perdas", ",",
    "casa", "povo", "&", "regional"
]

# === Define custom rule-based patterns ===
custom_patterns = [
    [{"LOWER": "anexo"}],
    [{"LOWER": "nota"}, {"LOWER": "curricular"}],
    [{"LOWER": "secretaria"}]
]
matcher.add("CUSTOM", custom_patterns)


def filter_nested_entities_by_tokens(entities):
    """Remove longer entities that are token-wise extensions of shorter ones"""
    from spacy.lang.pt import Portuguese
    nlp = Portuguese()

    tokenized = [(e, [t.text for t in nlp(e)]) for e in set(entities)]
    tokenized.sort(key=lambda x: len(x[1]))  # sort by number of tokens

    to_remove = set()
    for i, (short_ent, short_tokens) in enumerate(tokenized):
        for long_ent, long_tokens in tokenized[i+1:]:
            if long_tokens[:len(short_tokens)] == short_tokens:
                to_remove.add(long_ent)

    return set(e for e, _ in tokenized if e not in to_remove)









def trim_custom_from_person(person, custom_entities):
    """Cut off the person name at the point a custom entity starts."""
    lower_person = person.lower()
    cut_index = len(person)

    for ce in custom_entities:
        ce_lower = ce.lower()
        index = lower_person.find(ce_lower)
        if index != -1 and index < cut_index:
            cut_index = index

    return person[:cut_index].strip()



def remove_short_entities(entities, min_words=1):
    return {e for e in entities if len(e.split()) > min_words}

#Remove unwanted keywords
def remove_entities_with_keywords(entities, keywords):
    return {e for e in entities if not any(kw.lower() in e.lower() for kw in keywords)}



# === Combined HTML output ===
combined_html_path = os.path.join(HTML_DIR, "all_results.html")
with open(combined_html_path, "w", encoding="utf-8") as html_file:
    html_file.write("<html><head><meta charset='utf-8'><title>NER Results</title></head><body>\n")

    # === Process each .txt file ===
    for filename in os.listdir(INPUT_DIR):
        if filename.endswith(".txt"):
            path = os.path.join(INPUT_DIR, filename)
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()

            doc = nlp(text)

            # Match custom rules
            matches = matcher(doc)
            custom_entities = set(doc[start:end].text.strip() for _, start, end in matches)


            # Extract spaCy PER entities
            raw_persons = [ent.text.strip() for ent in doc.ents if ent.label_ == "PER"]
            trimmed_persons = [trim_custom_from_person(p, custom_entities) for p in raw_persons]
            filtered_persons = filter_nested_entities_by_tokens(trimmed_persons)
            filtered_persons = remove_short_entities(filtered_persons)
            filtered_persons = remove_entities_with_keywords(filtered_persons, UNWANTED_KEYWORDS)

            # Print to console
            print(f"\n📄 {filename}")
            print("👤 Pessoas detectadas:")
            if filtered_persons:
                for name in sorted(filtered_persons):
                    print(f"• {name}")
            else:
                print("• Nenhuma pessoa encontrada.")

            print("📌 Entidades personalizadas:")
            if custom_entities:
                for phrase in sorted(custom_entities):
                    print(f"• {phrase}")
            else:
                print("• Nenhuma encontrada.")

            # Write this document's section into combined HTML
            html_file.write(f"<h2>{filename}</h2>\n")
            html_file.write("<h3>Pessoas detectadas:</h3><ul>\n")
            for name in sorted(filtered_persons):
                html_file.write(f"<li>{name}</li>\n")
            html_file.write("</ul>\n<h3>Entidades personalizadas:</h3><ul>\n")
            for phrase in sorted(custom_entities):
                html_file.write(f"<li>{phrase}</li>\n")
            html_file.write("</ul><hr>\n")

    html_file.write("</body></html>")
