import requests
import re
import json
import xml.etree.ElementTree as ET
import time
import os

def get_ids_from_file(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return []
    with open(filepath, 'r') as f:
        urls = f.readlines()
    ids = []
    for url in urls:
        url = url.strip()
        if not url: continue
        match = re.search(r'(\d+\.\d+)', url)
        if match:
            ids.append(match.group(1))
    return ids

def fetch_arxiv_metadata(ids):
    base_url = "http://export.arxiv.org/api/query?id_list="
    batch_size = 50
    all_data = []

    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i:i+batch_size]
        url_ids = ",".join(batch_ids)
        url = f"{base_url}{url_ids}&max_results={len(batch_ids)}"
        print(f"Fetching batch {i} to {i+len(batch_ids)}...")
        try:
            response = requests.get(url)
            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                continue

            root = ET.fromstring(response.content)
            # Atom namespace
            ns = {'atom': 'http://www.w3.org/2005/Atom'}

            entries = root.findall('atom:entry', ns)
            print(f"Received {len(entries)} entries.")

            for entry in entries:
                id_text = entry.find('atom:id', ns).text
                # arXiv ID from url usually http://arxiv.org/abs/2101.00000v1
                arxiv_id_match = re.search(r'(\d+\.\d+)', id_text)
                arxiv_id = arxiv_id_match.group(1) if arxiv_id_match else id_text

                title_elem = entry.find('atom:title', ns)
                summary_elem = entry.find('atom:summary', ns)

                title = title_elem.text.strip().replace('\n', ' ') if title_elem is not None else "No Title"
                summary = summary_elem.text.strip().replace('\n', ' ') if summary_elem is not None else "No Summary"
                link = id_text.strip()

                all_data.append({
                    "id": arxiv_id,
                    "title": title,
                    "summary": summary,
                    "link": link
                })

            time.sleep(1) # Be nice to arXiv API
        except Exception as e:
            print(f"Exception: {e}")

    return all_data

def main():
    ids = get_ids_from_file("arxiv_urls.txt")
    print(f"Found {len(ids)} IDs.")
    if not ids:
        return

    data = fetch_arxiv_metadata(ids)

    output_path = "docs/arcticles/harvested.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved {len(data)} records to {output_path}")

if __name__ == "__main__":
    main()
