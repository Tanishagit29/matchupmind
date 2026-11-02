# MatchupMind AI

A cricket "what if?" simulator. Pick a batter and a bowler, generate a next-ball prediction, then change the bowler, batter, over or wickets lost and compare the predicted outcome distributions side by side.

- **Backend:** Python, FastAPI, Pandas, scikit-learn
- **Frontend:** React, Vite, Tailwind CSS, Recharts, Lucide icons
- **Data:** [Cricsheet](https://cricsheet.org/) ball-by-ball CSV files (T20)

> **Important:** predictions are statistical estimates from a trained model. Changing a scenario does not prove what would actually have happened.

## Project status

| Area | Status |
|---|---|
| Data prep (Cricsheet CSV2 and synthetic demo mode) | Done |
| Training with chronological match-based split and baselines | Done |
| Prediction, what-if and player-stats API | Done |
| React frontend (6 pages) | Done |
| Backend tests (pytest) | Done, 5 passing on demo data |
| Browser click-through and full real-data run | **Not yet verified by the author** |
| Turning-point / match-outcome insights | Not implemented (needs score and target features) |
| Field settings | Not implemented (Cricsheet has no field-placement data) |
| XGBoost, calibration curves, live-cricket API | Not implemented |

## How it works

- **Outcomes predicted per ball:** 0, 1, 2, 3, 4, 6 or wicket. Boundary probability is P(4) + P(6). Expected next-over runs is 6 × expected runs per ball, which is an approximation that ignores extras.
- **Split:** matches are sorted by date and split 70/15/15 into train, validation and test sets. A check fails training if training matches are not earlier than test matches.
- **Features:** batter and bowler career outcome rates (shrunk toward the league average, computed from training matches only), T20 phase, over, wickets lost and innings.
- **Model:** multinomial logistic regression, evaluated on the test split by log-loss and wicket Brier score against global-frequency and phase-frequency baselines. Results are shown on the Model page.
- **Head-to-head** numbers are shown as historical evidence. The model does not use them directly.
- **Small samples:** the API and UI warn when a player has fewer than 100 historical balls, or fewer than 12 head-to-head balls.
- **Labeling:** every response includes `data_source` (`cricsheet` or `DEMO_SYNTHETIC`), and the UI shows a badge for it. Nothing is hardcoded.
- **Briefings:** with `ANTHROPIC_API_KEY` set, the What-If briefing is written by an LLM from the computed numbers only. Without a key, or if the call fails, a template briefing is used. The response reports which one was used.

## Setup (Windows PowerShell)

Requirements: Python 3.10+, Node.js 18+, Git.

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt
```

### 2. Data

**Real data (recommended).** Download a T20 competition from <https://cricsheet.org/downloads/> in the **Ball-by-ball CSV2** format. Start with IPL; a larger dataset makes training slower.

```powershell
Invoke-WebRequest https://cricsheet.org/downloads/ipl_csv2.zip -OutFile ipl.zip
Expand-Archive ipl.zip -DestinationPath ipl_data -Force
python -m app.data_prep cricsheet --src .\ipl_data
```

The command should report `source=cricsheet` and a large ball count.

**Demo mode (pipeline testing only).** Generates synthetic data with invented players such as "Demo Batter 1". These are not real statistics.

```powershell
python -m app.data_prep demo
```

### 3. Train and run

```powershell
python -m app.train               # prints metrics and writes data\model.joblib
uvicorn app.main:app --reload     # API docs: http://127.0.0.1:8000/docs
```

Restart uvicorn after retraining. It keeps the old model in memory.

### 4. Frontend (second PowerShell window)

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev                       # http://localhost:5173
```

### 5. Tests

```powershell
cd backend
pytest -q
```

Tests train on a small synthetic dataset and do not need Cricsheet data.

## Configuration

Backend (environment variables, see `.env.example`):

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Optional. Enables LLM briefings. |
| `ANTHROPIC_MODEL` | Optional. Overrides the default model name. |
| `CORS_ORIGINS` | Allowed frontend origins (default `http://localhost:5173`). |
| `MM_MODEL_PATH`, `MM_BALLS_CSV` | Optional custom paths for the model and dataset. |

Set the key for one session with `$env:ANTHROPIC_API_KEY="your-key"` before starting uvicorn. Never commit keys or `.env` files.

Frontend: `VITE_API_URL` in `frontend/.env` (default `http://127.0.0.1:8000`).

## API

| Endpoint | Description |
|---|---|
| `GET /health` | Backend and model status |
| `GET /players?q=` | Player search |
| `GET /players/{name}/stats?role=batter\|bowler` | Historical stats and recent form |
| `POST /predict` | Next-ball prediction for one scenario |
| `POST /whatif` | Baseline vs. changed scenario, deltas and briefing |
| `GET /model/metrics` | Test metrics and split details |

Example:

```json
POST /whatif
{
  "baseline": {"batter": "V Kohli", "bowler": "JJ Bumrah", "over": 17, "wickets": 3},
  "changes": {"bowler": "Rashid Khan"}
}
```

Overs are 0-indexed (0 to 19). Player names must match Cricsheet spellings (initials plus surname), so use `/players?q=` or the in-app search.

## Troubleshooting

- **"Demo Batter" players appear:** the model was trained on demo data. Rebuild with `data_prep cricsheet`, retrain, restart uvicorn, then hard-refresh the browser (Ctrl+F5).
- **Home page says backend not reachable:** uvicorn is not running, or `VITE_API_URL` is wrong.
- **"Model not trained yet":** run `data_prep` and `train` first.
- **404 for a player:** that player has no records in the loaded data.
- **Training is slow:** features are built row by row. Try a smaller competition first.

## Project layout

```
backend/
  app/            data_prep, model, train, predict, briefing, main (FastAPI)
  tests/          pytest suite
  data/           generated dataset and model (git-ignored)
frontend/
  src/            App.jsx, Players.jsx, api.js
```

## Data attribution

Ball-by-ball data comes from [Cricsheet](https://cricsheet.org/) and is subject to its own terms. The data is not included in this repository. Download it yourself using the steps above.

## Limitations

- The model predicts the next ball only and does not use score, target or required run rate.
- Career rates ignore opposition, venue, pitch and recent form.
- Wickets lost is derived from the ball data, not supplied by a live feed.
- No probability calibration analysis has been done yet.