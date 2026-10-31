# Rastro — Web Change Intelligence

Rastro is a Python web-monitoring dashboard that tracks changes in public HTML pages. It stores page snapshots, compares new content with previous versions, and records detected additions and removals.

## Features

- Register and manage multiple pages.
- Fetch and extract readable text from HTML pages.
- Store historical snapshots in SQLite.
- Detect content changes between consecutive checks.
- Review added and removed line counts.
- Explore recent activity with a dashboard and charts.
- Compare the previous and current page text.

## Tech Stack

- Python
- Streamlit
- Requests
- BeautifulSoup
- SQLite
- Pandas
- Plotly

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Taunt-byte/Rastro-web-change-intelligence.git
cd rastro
```

### 2. Create a virtual environment

**Windows**
```bash
py -m venv .venv
.venv\Scripts\activate
```

**Linux / macOS**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
streamlit run app.py
```

The dashboard will open in your browser. The SQLite database (`rastro.db`) is created automatically.

## How It Works

1. Add a public HTTP or HTTPS page.
2. Run a check to fetch its HTML.
3. Rastro extracts readable text and saves a snapshot.
4. On subsequent checks, it compares the new text with the latest snapshot.
5. If differences are found, it records the event in the change history.

## Project Structure

```text
rastro/
├── app.py
├── database.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Current Limitations

- Checks are manually triggered in this MVP.
- Pages that render their content exclusively with JavaScript may not be captured.
- The comparison focuses on extracted text, not visual layout or source-code changes.
- This tool is intended for responsible monitoring of public pages. Always respect website terms, access policies, and rate limits.

## Roadmap

- [ ] Scheduled checks
- [ ] Email notifications
- [ ] Export change reports to PDF
- [ ] More robust content normalization
- [ ] Per-site check intervals
- [ ] Automated tests
- [ ] Docker deployment

## License

MIT
