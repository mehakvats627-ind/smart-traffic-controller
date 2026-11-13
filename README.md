# Smart Traffic Controller

A Streamlit control-room dashboard for a seeded four-way intersection simulation. It pairs fixed-time and Mamdani fuzzy control on the same vehicle arrival schedule, reports measured outcomes, and stores comparison runs in SQLite.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The simulation has no external map or service dependency. Pygame renders the top-down intersection to a headless surface that Streamlit displays as an image. The sidebar switches among Overview, Simulation, Fuzzy Logic, Analytics, Scenarios, and Reports.

## What is included

- Four approaches, four vehicle classes, seeded arrivals, queue tracking, service/travel/wait measurements, and safe following via discrete vehicle service times.
- Configurable fixed-time green phases and adaptive Mamdani inference with nine rules, centroid defuzzification, 10–60 second green bounds, aged-wait fairness, and ambulance priority.
- Demand profiles for normal, rush hour, unequal, low, emergency, and custom traffic.
- Paired controller comparisons, Plotly charts, SQLite history, CSV/JSON report exports, and JSON scenario configuration.

## Validation

Run `pytest` from the project directory. Tests cover all fuzzy rule combinations and bounds, clearance transitions, reproducible schedules, vehicle service, paired comparisons, and SQLite persistence.

## Measurement notes

The comparison uses identical seeded arrival events and vehicle types for each policy. Waiting time is measured from arrival to stop-line release; travel time is the simulated time until clearing the intersection. Runs are finite, so vehicles still in the system at the end contribute to current waiting time but not served-only travel-time and stop-count averages. Demand values are per-second Bernoulli arrival probabilities.
