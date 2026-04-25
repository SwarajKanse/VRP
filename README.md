# VRP Solver

Pure-stdlib Tkinter project for "VRP solver using GUI in Python".

## Run

```bash
python main.py
```

Or from the parent directory:

```bash
python -m VRP.main
```

## Scope

- Tkinter-only UI
- Explainable multi-depot CVRP solver
- Nearest-neighbour construction with 2-opt improvement
- Construction and final routes
- Step-by-step solver decisions with alternatives
- Blank network view and map background toggle
- Truck animation along road geometry
- Address geocoding and direct pin placement

## Notes

- Real road paths and geocoding use public Nominatim/OSRM endpoints via Python `urllib`.
- The app caches geocoding, route geometry, and map tiles under `cache/`.
- If APIs are unavailable, routing falls back to a cached or synthetic curved segment so the demo still runs.
