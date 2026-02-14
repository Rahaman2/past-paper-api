# NSC Past Papers API

A FastAPI-based REST API that scrapes and serves South African National Senior Certificate (NSC) past examination papers and memorandums from the Department of Basic Education.

## Features

- Download links for 60+ subjects (Languages, STEM, Business, Arts, etc.)
- Filter by year, session, and subject
- Papers available in English and Afrikaans
- Swagger UI documentation at `/docs`
- Pydantic models for type-safe responses

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

| Endpoint | Description |
|----------|-------------|
| `GET /` | API info and available endpoints |
| `GET /values` | **All acceptable parameter values** |
| `GET /sessions` | List all available exam sessions |
| `GET /sessions/{year}` | Get sessions for a specific year |
| `GET /papers/{year}/{session}` | Get papers grouped by subject |
| `GET /papers/{year}/{session}?subject=math` | Filter papers by subject |
| `GET /subjects/{year}/{session}` | List all subjects for a session |

## Parameter Values

Use `GET /values` to get all acceptable parameter values dynamically. Here's a summary:

### Session Types
| Value | Description |
|-------|-------------|
| `November` | Main NSC exams (October/November) |
| `MayJune` | Mid-year exams |
| `FebMarch` | Supplementary exams |
| `Supplementary` | Additional supplementary exams |

### Years
Years from 2008 to present (e.g., `2024`, `2025`)

### Subject Filter (`?subject=`)
The `subject` query parameter accepts **partial, case-insensitive matches**:

| Query | Matches |
|-------|---------|
| `?subject=math` | Mathematics, Mathematical Literacy, Technical Mathematics |
| `?subject=english` | English FAL, English HL |
| `?subject=english fal` | English FAL |
| `?subject=english hl` | English HL |
| `?subject=afrikaans` | Afrikaans FAL, Afrikaans HL, Afrikaans SAL |
| `?subject=isizulu` | IsiZulu FAL, IsiZulu HL |
| `?subject=physics` | Physical Sciences |
| `?subject=life` | Life Sciences |
| `?subject=accounting` | Accounting |
| `?subject=fal` | All FAL (First Additional Language) subjects |
| `?subject=hl` | All HL (Home Language) subjects |

**Examples:**
```bash
# Get English FAL papers
curl "http://localhost:8000/papers/2025/MayJune?subject=english fal"

# Get all Afrikaans variants (FAL, HL, SAL)
curl "http://localhost:8000/papers/2025/MayJune?subject=afrikaans"

# Get IsiZulu Home Language
curl "http://localhost:8000/papers/2025/MayJune?subject=isizulu hl"

# Get all Home Language subjects
curl "http://localhost:8000/papers/2025/MayJune?subject=hl"
```

### Languages
Papers are available in:
- `English`
- `Afrikaans`

### Paper Numbers
- `P1` - Paper 1
- `P2` - Paper 2
- `P3` - Paper 3

## Response Models

### PapersResponse

```json
{
  "year": "2025",
  "session": "MayJune",
  "source_url": "https://education.gov.za/...",
  "total_subjects": 61,
  "subjects": {
    "Mathematics": {
      "P1": {
        "paper": {
          "English": "https://education.gov.za/LinkClick.aspx?fileticket=...",
          "Afrikaans": "https://education.gov.za/LinkClick.aspx?fileticket=..."
        },
        "memo": {}
      },
      "P2": {
        "paper": {
          "English": "https://education.gov.za/LinkClick.aspx?fileticket=...",
          "Afrikaans": "https://education.gov.za/LinkClick.aspx?fileticket=..."
        },
        "memo": {}
      }
    },
    "Physical Sciences": {
      "P1": {
        "paper": {"English": "https://...", "Afrikaans": "https://..."},
        "memo": {}
      }
    }
  }
}
```

### SubjectsListResponse

```json
{
  "year": "2025",
  "session": "MayJune",
  "total": 61,
  "subjects": [
    "Accounting",
    "Afrikaans FAL",
    "Afrikaans HL",
    "Agricultural Sciences",
    "Business Studies",
    "Computer Application Technology",
    "Economics",
    "English FAL",
    "English HL",
    "Geography",
    "History",
    "Information Technology",
    "Life Sciences",
    "Mathematical Literacy",
    "Mathematics",
    "Physical Sciences",
    "..."
  ]
}
```

### AvailableValuesResponse

```json
{
  "sessions": ["November", "MayJune", "FebMarch", "Supplementary"],
  "years": ["2025", "2024", "2023", "..."],
  "sample_subjects": ["Accounting", "Mathematics", "Physical Sciences", "..."],
  "languages": ["English", "Afrikaans"],
  "paper_numbers": ["P1", "P2", "P3"]
}
```

## Usage Examples

### Get all acceptable parameter values
```bash
curl http://localhost:8000/values
```

### Get all 2025 exam sessions
```bash
curl http://localhost:8000/sessions/2025
```

### Get English FAL papers
```bash
curl "http://localhost:8000/papers/2025/MayJune?subject=english fal"
```

### Get English HL papers
```bash
curl "http://localhost:8000/papers/2025/MayJune?subject=english hl"
```

### Get all Afrikaans variants (FAL, HL, SAL)
```bash
curl "http://localhost:8000/papers/2025/MayJune?subject=afrikaans"
```

### Get IsiZulu Home Language papers
```bash
curl "http://localhost:8000/papers/2025/MayJune?subject=isizulu hl"
```

### Get Mathematics papers
```bash
curl "http://localhost:8000/papers/2025/MayJune?subject=math"
```

### Get all Home Language subjects
```bash
curl "http://localhost:8000/papers/2025/MayJune?subject=hl"
```

### Get all First Additional Language subjects
```bash
curl "http://localhost:8000/papers/2025/MayJune?subject=fal"
```

### List all subjects for a session
```bash
curl http://localhost:8000/subjects/2025/MayJune
```

## Available Subjects (60+)

The API provides papers for all NSC subjects including:

**Languages (11 official languages):**
- Afrikaans (FAL, HL, SAL)
- English (FAL, HL)
- IsiNdebele, IsiXhosa, IsiZulu (FAL, HL)
- Sepedi, Sesotho, Setswana, Siswati, Tshivenda, Xitsonga (FAL, HL)
- South African Sign Language (SASL)

**STEM:**
- Mathematics, Mathematical Literacy, Technical Mathematics
- Physical Sciences, Life Sciences, Technical Sciences
- Computer Application Technology, Information Technology
- Agricultural Sciences, Agricultural Technology

**Business & Commerce:**
- Accounting, Business Studies, Economics

**Arts & Culture:**
- Visual Arts, Design, Music, Dance Studies, Dramatic Arts

**Technical:**
- Civil Technology, Electrical Technology, Mechanical Technology
- Engineering Graphic and Design

**Other:**
- Geography, History, Tourism, Hospitality Studies
- Consumer Studies, Religion Studies

## Project Structure

```
past-paper-api/
├── main.py          # FastAPI application and endpoints
├── scraper.py       # Web scraping functions
├── models.py        # Pydantic response models
├── requirements.txt # Python dependencies
└── README.md
```

## Pydantic Models

All response models are defined in `models.py`:

| Model | Description |
|-------|-------------|
| `SessionsResponse` | Response for `/sessions` endpoint |
| `SessionsByYearResponse` | Response for `/sessions/{year}` endpoint |
| `PapersResponse` | Response for `/papers/{year}/{session}` endpoint |
| `SubjectsListResponse` | Response for `/subjects/{year}/{session}` endpoint |
| `AvailableValuesResponse` | Response for `/values` endpoint |
| `ExamSession` | Individual session object |
| `PaperLinks` | Paper/memo download links by language |

## Data Source

Papers are scraped from the official Department of Basic Education website:
- **education.gov.za** - Official DBE NSC past papers portal

## Tech Stack

- Python 3.10+
- FastAPI
- Pydantic v2
- BeautifulSoup4
- Requests
- Uvicorn

## Deployment (Contabo Server)

### Live URLs
| Service | URL |
|---------|-----|
| Frontend | https://matricmate.co.za |
| API | https://api.matricmate.co.za |
| API Docs | https://api.matricmate.co.za/docs |

### Deploy Updates

After pushing changes to the `main` branch, SSH into the server and run:

```bash
ssh root@185.190.140.123
/var/www/deploy.sh
```

This script will:
1. Pull latest changes for the API
2. Install any new Python dependencies
3. Restart the API service
4. Pull latest changes for the frontend
5. Install any new npm dependencies
6. Rebuild the Next.js app
7. Restart the frontend

### Manual Commands

**API:**
```bash
cd /var/www/api
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
deactivate
sudo systemctl restart pastpaper-api
sudo systemctl status pastpaper-api
```

**Frontend:**
```bash
cd /var/www/matricmate
git pull origin main
npm install
npm run build
pm2 restart matricmate
pm2 status
```

### Logs

```bash
# API logs
sudo journalctl -u pastpaper-api -f

# Frontend logs
pm2 logs matricmate

# Nginx logs
sudo tail -f /var/log/nginx/error.log
```

### Ports

| Service | Port |
|---------|------|
| API | 10000 |
| Frontend | 10001 |

## License

MIT
