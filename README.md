# PDF Index Search

A desktop app for searching keywords in PDFs. Open a document, search by comma separated terms, browse matches in the index panel, and export a highlighted copy.

## Requirements

- Python 3.10+
- macOS, Windows, or Linux

## Setup

```bash
git clone https://github.com/filipolz/pdf-index-search.git
cd pdf-index-search
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Usage

1. Click **Open PDF** and select a file.
2. Enter keywords separated by commas (e.g. `contract, liability, warranty`).
3. Click **Search** to highlight matches and list them in the side panel.
4. Click a result to jump to that page.
5. Click **Export PDF** to save a highlighted copy.
