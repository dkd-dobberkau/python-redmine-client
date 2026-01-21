# Redmine Client

Python-Client für die Redmine REST-API mit Unterstützung für synchrone und asynchrone Operationen.

## Features

- Synchroner und asynchroner Client
- Vollständige Typisierung mit Pydantic-Modellen
- Custom Fields Unterstützung
- Automatische Paginierung
- Context Manager Support

## Installation

```bash
pip install redmine-client
```

Oder für Entwicklung:

```bash
pip install -e ".[dev]"
```

## Verwendung

### Synchron

```python
from redmine_client import RedmineClient

with RedmineClient("https://redmine.example.com", "your-api-key") as client:
    # Alle mir zugewiesenen offenen Issues
    issues = client.get_issues(assigned_to_id="me", status_id="open")

    for issue in issues:
        print(f"#{issue.id}: {issue.subject}")

    # Issue mit Custom Field aktualisieren
    client.update_issue(
        issue_id=123,
        custom_fields=[{"id": 42, "value": "2026-KW03-KW04"}]
    )
```

### Asynchron

```python
from redmine_client import AsyncRedmineClient

async with AsyncRedmineClient("https://redmine.example.com", "your-api-key") as client:
    issues = await client.get_issues(assigned_to_id="me", status_id="open")

    for issue in issues:
        print(f"#{issue.id}: {issue.subject}")
```

## API

### Issues

```python
# Issues abrufen
issues = client.get_issues(
    project_id="myproject",      # Optional: Filter nach Projekt
    assigned_to_id="me",         # Optional: Filter nach Zuweisung
    status_id="open",            # Optional: "open", "closed", "*", oder ID
    tracker_id=1,                # Optional: Bug, Feature, etc.
)

# Einzelnes Issue
issue = client.get_issue(123, include_journals=True)

# Issue erstellen
new_issue = client.create_issue(
    project_id="myproject",
    subject="Neues Feature",
    description="Beschreibung...",
    tracker_id=2,
    custom_fields=[{"id": 42, "value": "Sprint-Wert"}]
)

# Issue aktualisieren
client.update_issue(
    issue_id=123,
    subject="Neuer Betreff",
    notes="Kommentar hinzufügen",
    custom_fields=[{"id": 42, "value": "Neuer Wert"}]
)

# Kommentar hinzufügen
client.add_issue_note(123, "Mein Kommentar")
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

### Enumerationen

```python
trackers = client.get_trackers()
statuses = client.get_issue_statuses()
priorities = client.get_issue_priorities()
activities = client.get_time_entry_activities()
```

## Modelle

Alle Antworten werden als Pydantic-Modelle zurückgegeben:

- `RedmineIssue` - Issue/Ticket
- `RedmineProject` - Projekt
- `RedmineUser` - Benutzer
- `RedmineTimeEntry` - Zeitbuchung
- `RedmineCustomField` - Custom Field Wert
- `RedmineCustomFieldDefinition` - Custom Field Definition

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

## Lizenz

MIT
