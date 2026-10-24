# Savannah clinic booking API

Doctor–patient appointment booking API (Django + DRF + PostgreSQL).

## System design

See [docs/SystemDesignDoc.md](docs/SystemDesignDoc.md).

## Live app

**Public URL:** [https://kigendemo.online](https://kigendemo.online)

## Postman

Collection file: [docs/savannah.postman_collection.json](docs/savannah.postman_collection.json)

Copy that file and import it into Postman. The admin password is in the submission email for recruiters — it is not committed here. Keeping credentials out of this public repo avoids strangers hitting and bloating my live server.

## CI/CD

Pushing to the `deploy` branch (or running the workflow manually) starts GitHub Actions.

| Job | When | What it does |
|---|---|---|
| **test** | Always on that run | Starts Postgres, installs dependencies, migrates, runs `manage.py test` |
| **deploy** | Only if tests pass | SSHs to the VPS as `SSH_USER`, resets `VPS PATH` to `origin/deploy`, reinstalls the venv, migrates, runs `collectstatic`, restarts `savannah.service` |

## AI reflection

### 1. What did you use AI for across the four sections?

- **Section 2 (API):** Commenting, checking the implementation against the assessment brief, and refactoring to match my design patterns (service layer, folder-by-feature layout).
- **Section 3 (Deploy / CI):** Drafting CI/CD from my existing, battle-tested Django deploy scripts so the pipeline matched how I already ship apps.

### 2. Give one example where an AI suggestion improved your work. What did you prompt it with?

AI helped restructure routing so the API matched the required endpoints, and helped me diff the codebase against the written requirements. A sample of that prompt is in [docs/prompsample.md](docs/prompsample.md).

### 3. Give one example where AI output was wrong or incomplete and how you caught it?

- Seed data: Cursor tried to hardcode default admin passwords. I stopped that and kept credentials in environment variables only.
- API errors: It returned custom response codes and shapes I did not want. I specified the exact `status` / `error` / `message` contract and verified every case in Postman, endpoint by endpoint.

### 4. Name two decisions you made without AI. Why did you trust your own judgment there?

1. **Database design** — I own the ERD and relationships in the design phase. I do not want a generated schema that looks fine but is weak under real booking load.
2. **VPS prep and migrations** — SSH, first-time migrate/seed, and server readiness stay manual before I trust CI/CD against the box.
3. **Postman verification** — Full collection runs are mine. I walk each endpoint myself so the live system matches what the brief asks for.

