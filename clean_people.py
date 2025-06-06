import spacy
import os

from rich.console import Console

# === Config ===
NLP_MODEL = "pt_core_news_lg"
#INPUT_DIR = "raw_TXT"

TRIM_KEYWORDS = ["anexo", "nota curricular", "secretaria"]

UNWANTED_WORDS = [
    "formação", "profissional", "infraestruturas", "despacho", "conjunto", "madeira",
    "câmara", "chefe", "estudos", "coordenação", "autoridade", "assuntos",
    "fiscais", "regional", "secretária", "&", "diretor", "diretora",
    "habilitações", "literárias", "professor", "professora", "convidado", "convidada",
    "sistemas", "informação", "tecnologias", "especialista", "recursos", "humanos",
    "apoio", "família", "idosa", "idoso", "assistente",
    "vogal", "conselho", "diretivo", "bilhete", "identidade", "inspetora", "tributária",
    "tributário", "secundária", "bolseiro", "bolseira", "investigador", "investigadora"
]



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

def remove_entities_with_unwanted_words(entities, unwanted_words):
    unwanted_words_lower = [w.lower() for w in unwanted_words]
    filtered = []
    for ent in entities:
        ent_words = ent.lower().split()
        if not any(word in ent_words for word in unwanted_words_lower):
            filtered.append(ent)
    return filtered


def extract_clean_person_entities(input_dir: str) -> dict:
    results = {}
    INPUT_DIR = input_dir

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
            person_entities = remove_entities_with_unwanted_words(person_entities, UNWANTED_WORDS)

            results[filename] = person_entities
            

    return results

console = Console()
results = extract_clean_person_entities("raw_TXT")

for filename, people in results.items():
    console.print(f"[bold blue]{filename}[/bold blue]")
    for person in people:
        console.print(f"  - [green]{person}[/green]")