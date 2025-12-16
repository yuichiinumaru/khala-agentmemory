import os
import time
import requests
import sys

# Constants
PDF_DIR = "docs/arxiv"
ID_FILE = "scripts/research/target_papers.txt"
BASE_URL = "https://arxiv.org/pdf/{}.pdf"

def fetch_papers():
    if not os.path.exists(PDF_DIR):
        os.makedirs(PDF_DIR)
        print(f"Created directory: {PDF_DIR}")

    if not os.path.exists(ID_FILE):
        print(f"Error: {ID_FILE} not found.")
        return

    with open(ID_FILE, 'r') as f:
        # Filter empty lines and comments
        lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    total = len(lines)
    print(f"Found {total} papers to process.")

    for i, line in enumerate(lines):
        # Extract ID
        # Logic: if it looks like a url, split by / and take last element. Remove .pdf if present.
        clean_line = line.replace('.pdf', '')
        if '/' in clean_line:
            paper_id = clean_line.split('/')[-1]
        else:
            paper_id = clean_line

        # Target file path
        pdf_path = os.path.join(PDF_DIR, f"{paper_id}.pdf")

        if os.path.exists(pdf_path):
            print(f"[{i+1}/{total}] Skipping {paper_id} (already exists)")
            continue

        url = BASE_URL.format(paper_id)
        # Handle cases where ID already has suffix or is special, but generally arxiv url is simply ID.pdf
        # If the user provided URL ends in v1/v2, we stripped .pdf (which wasn't there) and take the last part.

        print(f"[{i+1}/{total}] Downloading {paper_id} from {url}...")

        try:
            response = requests.get(url, timeout=30, headers={"User-Agent": "Research-Pipeline-Bot/1.0"})
            if response.status_code == 200:
                with open(pdf_path, 'wb') as f:
                    f.write(response.content)
                print(f"  Success.")
            else:
                print(f"  Failed with status code: {response.status_code}")
        except Exception as e:
            print(f"  Error: {e}")

        # Be polite to Arxiv
        time.sleep(3)

if __name__ == "__main__":
    fetch_papers()
