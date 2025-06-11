import os
import json



def update_json_files_in_directory(directory_path: str):
    for filename in os.listdir(directory_path):
        if filename.endswith(".json"):
            file_path = os.path.join(directory_path, filename)

            # Load the JSON data
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            updated = False  # Track if file needs to be saved

            # Traverse top-level keys (secretarias)
            for secretaria, entries in data.items():
                for despacho_key, entry in entries.items():
                    text = entry.get("chunk", "")

                    # Update fields
                    new_data = extract_date_from_text(text)
                    new_autor = extract_people_from_chunk(text)

                    if entry.get("data") != new_data:
                        entry["data"] = new_data
                        updated = True

                    if entry.get("autor") != new_autor:
                        entry["autor"] = new_autor
                        updated = True

            # Save changes if any
            if updated:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

