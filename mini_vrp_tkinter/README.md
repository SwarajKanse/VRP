# Mini Tkinter VRP Solver

Pure-stdlib mini project for "VRP solver using GUI in Python".

## Run

```bash
python -m mini_vrp_tkinter.main
```

## Scope

- Tkinter-only UI
- Explainable Clarke-Wright savings solver
- Baseline, savings-stage, and final routes
- Step-by-step solver decisions with alternatives
- Blank network view and map background toggle
- Truck animation along road geometry
- Address geocoding and direct pin placement

## Notes

- Real road paths and geocoding use public Nominatim/OSRM endpoints via Python `urllib`.
- The app caches geocoding, route geometry, and map tiles under `mini_vrp_tkinter/cache`.
- If APIs are unavailable, routing falls back to a cached or synthetic curved segment so the demo still runs.

