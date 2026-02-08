# Redmine Client

[![PyPI version](https://badge.fury.io/py/redmine-client.svg)](https://pypi.org/project/redmine-client/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Python-Client für die Redmine REST-API mit Unterstützung für synchrone und asynchrone Operationen.

## Features

- Synchroner und asynchroner Client
- Vollständige Typisierung mit Pydantic-Modellen
- Issues mit Journals, Attachments, Relationen, Beobachtern, Changesets, Unteraufgaben
- Wiki-API (CRUD)
- Attachment-Upload und -Download
- Custom Fields Unterstützung
- Automatische Paginierung
- Context Manager Support

## Installation

```bash
pip install redmine-client
```

Oder mit uv:

```bash
uv add redmine-client
```

## Schnellstart

### Synchron

```python
from redmine_client import RedmineClient

with RedmineClient("https://redmine.example.com", "your-api-key") as client:
    issues = client.get_issues(assigned_to_id="me", status_id="open")

    for issue in issues:
        print(f"#{issue.id}: {issue.subject}")
```

### Asynchron

```python
from redmine_client import AsyncRedmineClient

async with AsyncRedmineClient("https://redmine.example.com", "your-api-key") as client:
    issues = await client.get_issues(assigned_to_id="me", status_id="open")

    for issue in issues:
        print(f"#{issue.id}: {issue.subject}")
```

## API-Referenz

### Issues

```python
# Issues mit Filtern abrufen
issues = client.get_issues(
    project_id="myproject",
    assigned_to_id="me",
    status_id="open",            # "open", "closed", "*" oder ID
    tracker_id=1,
    updated_on=">=2025-01-01",
    created_on=">=2025-01-01",
)

# Einzelnes Issue mit zugehörigen Daten abrufen
issue = client.get_issue(123, include=[
    "journals",           # Kommentare und Änderungshistorie
    "attachments",        # Dateianhänge
    "relations",          # Verknüpfte Issues
    "watchers",           # Beobachter
    "changesets",         # VCS-Commits
    "children",           # Unteraufgaben
    "allowed_statuses",   # Verfügbare Status-Übergänge
])

# Auf enthaltene Daten zugreifen
for journal in issue.journals or []:
    print(f"{journal.user_name}: {journal.notes}")

for attachment in issue.attachments or []:
    print(f"{attachment.filename} ({attachment.filesize} Bytes)")

for child in issue.children or []:
    print(f"  Unteraufgabe #{child.id}: {child.subject}")

# Issue erstellen
new_issue = client.create_issue(
    project_id="myproject",
    subject="Neues Feature",
    description="Beschreibung...",
    tracker_id=2,
    custom_fields=[{"id": 42, "value": "Sprint-Wert"}],
)

# Issue aktualisieren
client.update_issue(
    issue_id=123,
    subject="Neuer Betreff",
    status_id=2,
    notes="Kommentar hinzufügen",
    custom_fields=[{"id": 42, "value": "Neuer Wert"}],
)

# Kommentar hinzufügen
client.add_issue_note(123, "Mein Kommentar")
```

### Wiki

```python
# Wiki-Seiten auflisten
pages = client.get_wiki_pages("myproject")

for page in pages:
    print(page.title)

# Wiki-Seite abrufen
page = client.get_wiki_page("myproject", "Start", include_attachments=True)
print(page.text)
print(f"Autor: {page.author_name}, Version: {page.version}")

# Wiki-Seite erstellen oder aktualisieren
client.create_or_update_wiki_page(
    "myproject", "NeuSeite",
    text="h1. Seitentitel\n\nInhalt hier.",
    comments="Erste Version",
)

# Wiki-Seite löschen
client.delete_wiki_page("myproject", "AlteSeite")
```

### Attachments

```python
# Datei hochladen und Token erhalten
token = client.upload_file("/pfad/zu/dokument.pdf")

# Oder Bytes direkt hochladen
token = client.upload_file(b"Dateiinhalt", filename="daten.csv")

# An Issue anhängen via Erstellen oder Aktualisieren
client.create_issue(
    project_id="myproject",
    subject="Issue mit Anhang",
    uploads=[{
        "token": token,
        "filename": "dokument.pdf",
        "content_type": "application/pdf",
    }],
)

# Attachment-Metadaten abrufen
attachment = client.get_attachment(42)
print(f"{attachment.filename} - {attachment.filesize} Bytes")

# Attachment herunterladen
data = client.download_attachment(42)
with open("heruntergeladen.pdf", "wb") as f:
    f.write(data)

# Attachment löschen
client.delete_attachment(42)
```

### Custom Fields

```python
# Alle Custom Fields abrufen (benötigt Admin-Rechte)
fields = client.get_custom_fields()

# Nur Issue Custom Fields
issue_fields = client.get_issue_custom_fields()

# Custom Field nach Namen suchen
sprint_field = client.find_custom_field_by_name("Sprint")

# Custom Field Wert aus Issue lesen
issue = client.get_issue(123)
sprint = issue.get_custom_field("Sprint")
sprint_by_id = issue.get_custom_field_by_id(42)
```

### Projekte

```python
projects = client.get_projects(include_closed=False)
project = client.get_project("myproject")
```

### Benutzer

```python
current_user = client.get_current_user()
users = client.get_users(status=1)  # 1 = aktiv
user = client.get_user(42)
```

### Zeitbuchungen

```python
from datetime import date

entries = client.get_time_entries(
    user_id=1,
    from_date=date(2025, 1, 1),
    to_date=date(2025, 12, 31),
)
entry = client.get_time_entry(42)
```

### Enumerationen

```python
trackers = client.get_trackers()
statuses = client.get_issue_statuses()
priorities = client.get_issue_priorities()
activities = client.get_time_entry_activities()
```

## Modelle

Alle Antworten werden als Pydantic-Modelle zurückgegeben:

| Modell | Beschreibung |
|--------|-------------|
| `RedmineIssue` | Issue/Ticket mit optionalen Journals, Attachments, Relationen, Beobachtern, Changesets, Unteraufgaben |
| `RedmineProject` | Projekt |
| `RedmineUser` | Benutzer |
| `RedmineTimeEntry` | Zeitbuchung |
| `RedmineJournal` | Kommentar/Änderungshistorie |
| `RedmineJournalDetail` | Einzelne Feldänderung innerhalb eines Journals |
| `RedmineAttachment` | Dateianhang |
| `RedmineRelation` | Issue-Relation |
| `RedmineChangeset` | VCS-Commit |
| `RedmineAllowedStatus` | Erlaubter Status-Übergang |
| `RedmineWikiPage` | Wiki-Seite |
| `RedmineCustomField` | Custom Field Wert |
| `RedmineCustomFieldDefinition` | Custom Field Definition |

## Fehlerbehandlung

```python
from redmine_client import (
    RedmineError,
    RedmineAuthenticationError,
    RedmineNotFoundError,
    RedmineValidationError,
)

try:
    issue = client.get_issue(99999)
except RedmineNotFoundError:
    print("Issue nicht gefunden")
except RedmineAuthenticationError:
    print("API-Key ungültig")
except RedmineValidationError as e:
    print(f"Validierungsfehler: {e.response}")
except RedmineError as e:
    print(f"Redmine-Fehler: {e}")
```

## Entwicklung

```bash
git clone https://github.com/dkd-dobberkau/python-redmine-client.git
cd python-redmine-client
uv sync --all-extras
uv run pytest tests/ -v
uv run ruff check src/ tests/
```

## Lizenz

MIT
