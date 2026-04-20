# Quick Start

## 1. Install

Windows:

```bash
setup.bat
```

Linux/macOS:

```bash
chmod +x setup.sh
./setup.sh
```

Manual install:

```bash
python -m pip install -e .[dev]
```

## 2. Verify

```bash
python test_installation.py
```

## 3. Run

```bash
python -m vrp_platform.ui.app
```

Open [http://localhost:8080](http://localhost:8080).

## 4. Run focused checks

```bash
python -m pytest tests/platform -q
```

## Notes

- Local development uses SQLite by default.
- Set `VRP_DATABASE_URL` to move to PostgreSQL.
- Use the dispatcher page for manifest intake, filtered planning, scenario preview, route board, warehouse loading, and incident-aware live map views.
