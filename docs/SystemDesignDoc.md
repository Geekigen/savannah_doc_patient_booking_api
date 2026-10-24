# System Design — Savannah Clinic Booking API

## What we are building

A small clinic with five doctors. Patients book 30-minute slots online, see what is free for a doctor on a given day, and can cancel or reschedule. The clinic is small today but should still work when traffic grows.

## Design references

| Document | What it shows |
|---|---|
| [paperdraft.jpeg](paperdraft.jpeg) | Early notebook sketch — doctors, patients, 30-minute slots, cancel, and growth |
| [savannaherd.drawio.pdf](savannaherd.drawio.pdf) | Final ERD — `doctors`, `patients`, `slots`, and `appointments` |

The sections below turn that sketch and ERD into the running system.

---

## Models

The schema follows the ERD above.

**Shared bases**

- `BaseModel` — UUID id, created/modified timestamps, and a `synced` flag. Every table inherits this so we do not repeat the same fields.
- `GenericBaseModel` — adds `name` and `description` for lookup tables like `State`.

**Domain**

- `Doctor` — owns a day of 30-minute `Slot`s (08:00 through 14:30).
- `Patient` — books appointments.
- `Slot` — one start time on a doctor’s template. The same clock time can be booked on different dates.
- `Appointment` — a patient, a slot, and a date.
- `State` — seeded labels (`Booked`, `Cancelled`, and so on). Appointments point to `State` with a foreign key.

**Why State is a foreign key**

Filtering large appointment lists by status stays clear, and new statuses can be added without changing a choices field. The trade-off is one extra table and join.

**Keeping slots unique under load**

An active booking is unique per `(slot, date)`. Booking and reschedule lock the row in a transaction so two patients cannot take the same opening.

---

## Components

| Piece | Job |
|---|---|
| `api/auth` | Login and token |
| `api/doctors` | List doctors and availability |
| `api/patients` | List patients and upcoming visits |
| `api/appointments` | Book, cancel, reschedule |
| `base/models` | Database models |
| `base/backend` | Business rules (services). Views stay thin |
| `base/seed` | Admin, five doctors, four patients from env |
| PostgreSQL | Database |
| CI/CD | Tests, then deploy |

Folders are named after what they do, so the layout stays easy to follow.

---

## Key decisions

**PostgreSQL**

Chosen for growth, transactions, and locking under concurrent booking. Safer than SQLite once more than one client hits the same slot. Setup costs more locally; that is fine for a production-minded API.

**Django + DRF**

Chosen for clear routing, JSON responses, and built-in token auth. Faster to ship for this assessment than FastAPI or Go. The stack is heavier; the gain is delivery speed and structure.

**Token auth for one admin**

Login is public. Everything else needs `Authorization: Token …`. Simple for an admin-operated API. Patient or doctor login can come later without redesigning the models.

**Fixed slot grid**

Slots are created once per doctor. Availability is that grid minus bookings for the day (and past / within-one-hour rules). Easier to lock and constrain than inventing times on every request.

**Other choices**

- Timezone: Africa/Nairobi  
- Success responses: HTTP 200  
- Errors: `status`, `error`, `message` only  

---

## Trade-offs in short

| Choice | Gain | Cost |
|---|---|---|
| PostgreSQL | Scale and safe concurrent writes | More ops than SQLite |
| State as FK | Clear filters, easy to extend | Extra join |
| UUID ids | Safe across environments | Larger than integer ids in the ERD sketch |
| Django + DRF | Fast to build, token auth | Heavier than a minimal API |
| Services in `base/backend` | Thin views, reusable rules | More files |

---

## Growth

More doctors and patients are just more rows. Booking stays safe with transactions and the unique constraint. New endpoints can live in new folders under `api/`. Auth can grow to JWT or patient login without changing the core model.
