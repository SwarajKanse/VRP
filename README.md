# VRP Platform

Pure-Python vehicle routing platform built around `src/vrp_platform`.

## What it is

- NiceGUI control tower for dispatchers, customers, and drivers
- SQLAlchemy persistence with SQLite for local development and PostgreSQL-ready configuration
- Pure-Python optimizer with fleet-aware cost, fuel, break, time-window, and incident handling
- Warehouse load sheets, shipment tracking, and driver route execution views

## Current focus

This repository is now platform-only. The old standalone solver and dashboard path has been retired.

## Run locally

```bash
python -m pip install -e .[dev]
python -m vrp_platform.ui.app
```

The app opens on [http://localhost:8080](http://localhost:8080) by default.

## Verify the install

```bash
python test_installation.py
```

## Focused checks

```bash
python -m pytest tests/platform -q
```

## Main project areas

- `src/vrp_platform/domain` - typed entities and enums
- `src/vrp_platform/optimizer` - route construction, local search, and objectives
- `src/vrp_platform/repos` - persistence and read models
- `src/vrp_platform/services` - planning, ingestion, manifests, operations
- `src/vrp_platform/ui` - NiceGUI application

## Key environment settings

- `VRP_DATABASE_URL` - defaults to local SQLite
- `VRP_REDIS_URL` - queue backend target when enabling workers
- `VRP_TIMEZONE` - timezone for operational timestamps

## Operational note

The platform currently includes dispatcher filtering and paging, targeted order selection, warehouse load sheets, driver route maps, and incident-aware travel penalties. The next production steps are auth hardening, real telematics, external traffic feeds, and queue-backed long-running jobs.
