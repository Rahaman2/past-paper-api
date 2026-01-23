# NSC Past Papers API

A FastAPI-based REST API that scrapes and serves South African National Senior Certificate (NSC) past examination papers and memorandums.

## Features

- Fetches exam papers from two sources:
  - **DBE (Department of Basic Education)** - Languages and Technical subjects
  - **Eastern Cape Examinations** - All 46+ subjects including Mathematics, Physical Sciences, etc.
- Returns structured JSON with download links for question papers and memos
- Filter by year, session, and subject
- Swagger UI documentation at `/docs`

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd past-paper-api

# Install dependencies
pip install -r requirements.txt

# Run the server
python main.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Root
```
GET /
```
Returns available endpoints and data sources.

### Eastern Cape (All Subjects)

| Endpoint | Description |
|----------|-------------|
| `GET /ec/sessions` | List all available exam sessions |
| `GET /ec/sessions/{year}` | Get sessions for a specific year |
| `GET /ec/papers/{year}/{session}` | Get papers grouped by subject |
| `GET /ec/subjects/{year}/{session}` | List all subjects for a session |

### DBE (Languages & Technical)

| Endpoint | Description |
|----------|-------------|
| `GET /dbe/sessions` | List all available exam sessions |
| `GET /dbe/sessions/{year}` | Get sessions for a specific year |
| `GET /dbe/papers/{year}/{session}` | Get papers grouped by subject |

## Usage Examples

### Get all 2024 exam sessions
```bash
curl http://localhost:8000/ec/sessions/2024
```

### Get Mathematics papers for November 2024
```bash
curl "http://localhost:8000/ec/papers/2024/November?subject=math"
```

Response:
```json
{
  "source": "ecexams",
  "year": "2024",
  "session": "November",
  "total_subjects": 3,
  "subjects": {
    "Mathematics": {
      "P1": {
        "paper": "http://www.ecexams.co.za/.../Mathematics P1 Nov 2024.zip",
        "memo": "http://www.ecexams.co.za/.../Mathematics P1 Nov 2024 MG Afr & Eng.zip"
      },
      "P2": {
        "paper": "http://www.ecexams.co.za/.../Mathematics P2 Nov 2024.zip",
        "memo": "http://www.ecexams.co.za/.../Mathematics P2 Nov 2024 MG Afr & Eng.zip"
      }
    },
    "Mathematical Literacy": { ... },
    "Technical Mathematics": { ... }
  }
}
```

### List all subjects for a session
```bash
curl http://localhost:8000/ec/subjects/2024/November
```

## Available Sessions

- **November** - Main NSC exams
- **MayJune** - Mid-year exams
- **September** - Trial/Preparatory exams
- **FebMarch** - Supplementary exams

## Available Subjects (Eastern Cape)

Includes 46+ subjects:
- Accounting
- Afrikaans (FAL, HL, SAL)
- Agricultural Sciences
- Business Studies
- Computer Applications Technology
- Economics
- English (FAL, HL)
- Geography
- History
- Information Technology
- Life Sciences
- Mathematical Literacy
- Mathematics
- Physical Sciences
- Technical Mathematics
- Technical Sciences
- Visual Arts
- All 11 official South African languages
- And more...

## Project Structure

```
past-paper-api/
├── main.py          # FastAPI application and endpoints
├── scraper.py       # Web scraping functions for both sources
├── models.py        # Pydantic data models
├── requirements.txt # Python dependencies
└── README.md
```

## Data Sources

1. **education.gov.za** - Official Department of Basic Education website
2. **ecexams.co.za** - Eastern Cape Department of Education examinations portal

## Tech Stack

- Python 3.10+
- FastAPI
- BeautifulSoup4
- Requests
- Uvicorn

## License

MIT
