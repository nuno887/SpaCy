import os
import re
import pdfplumber

# === Config ===
INPUT_DIR = "input_PDF"
RAW_TXT_DIR = "raw_TXT"           # NEW: Stores raw output from PDF
OUTPUT_DIR = "output_TXT"
HTML_DIR = "html_output"

# Ensure directories exist
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(RAW_TXT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(HTML_DIR, exist_ok=True)

def load_txt_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

def extract_text_from_pdf(filepath):
    with pdfplumber.open(filepath) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)

def clean_text_into_paragraphs(text):
    text = text.strip()
    text = re.sub(r'\n{2,}', '<PARAGRAPH>', text)
    text = re.sub(r'\n', ' ', text)
    text = re.sub(r'<PARAGRAPH>', '\n\n', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()

def save_html(paragraphs, output_path):
    html = "<html><head><meta charset='utf-8'><title>Cleaned Text</title></head><body>\n"
    for p in paragraphs.split("\n\n"):
        html += f"<p>{p.strip()}</p>\n"
    html += "</body></html>"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

def process_file(filepath, filename):
    print(f"🧹 Processing: {filename}")
    if filename.endswith(".pdf"):
        raw_text = extract_text_from_pdf(filepath)

        # Save raw text before cleaning
        raw_output_path = os.path.join(RAW_TXT_DIR, f"{os.path.splitext(filename)[0]}.raw.txt")
        with open(raw_output_path, "w", encoding="utf-8") as f:
            f.write(raw_text)
        print(f"📄 Saved raw text to: {raw_output_path}")

    elif filename.endswith(".txt"):
        raw_text = load_txt_file(filepath)
    else:
        print(f"⏭️ Skipping unsupported file: {filename}")
        return

    cleaned = clean_text_into_paragraphs(raw_text)

    base_name = os.path.splitext(filename)[0]
    cleaned_txt_path = os.path.join(OUTPUT_DIR, f"{base_name}.cleaned.txt")
    html_output_path = os.path.join(HTML_DIR, f"{base_name}.html")

    with open(cleaned_txt_path, "w", encoding="utf-8") as f:
        f.write(cleaned)

    save_html(cleaned, html_output_path)

    print(f"✅ Saved cleaned text to: {cleaned_txt_path}")
    print(f"🌐 Saved HTML to: {html_output_path}")

def main():
    print(f"\n📂 Reading files from: {INPUT_DIR}\n")
    files = os.listdir(INPUT_DIR)
    if not files:
        print("⚠️ No files found in input/. Add PDFs or TXTs to process.")
        return

    for filename in files:
        filepath = os.path.join(INPUT_DIR, filename)
        process_file(filepath, filename)

    print("\n🎉 All done!")

if __name__ == "__main__":
    main()
