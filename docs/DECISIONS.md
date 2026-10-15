# Décisions techniques

## ADR-001 — Gestionnaire de dépendances : uv

- **Date** : 2026-10-10
- **Statut** : Accepté
- **Décision** : Utiliser `uv` + `dependency-groups` pour les deps de dev.

## ADR-002 — Build backend : hatchling

- **Date** : 2026-10-10
- **Statut** : Accepté

## ADR-003 — Framework web : FastAPI

- **Date** : 2026-10-10
- **Statut** : Accepté

## ADR-004 — Tests : pytest + httpx + TestClient

- **Date** : 2026-10-10
- **Statut** : Accepté

## ADR-005 — ORM + migrations : SQLAlchemy 2.0 + Alembic

- **Date** : 2026-10-10
- **Statut** : Accepté
- **Décision** :
  - SQLAlchemy 2.0 (`Mapped` / `mapped_column`)
  - Driver async : `asyncpg`
  - Driver sync pour Alembic : `psycopg[binary]`
  - UUID généré côté Python à l'instantiation (`__init__`)
  - `DATABASE_URL` via `.env` (chargé par `python-dotenv` dans `env.py`)

## ADR-006 — Python version

- **Date** : 2026-10-10
- **Statut** : Accepté
- **Décision** : Python 3.12, `requires-python = ">=3.11"`

## ADR-007 — Multi-tenancy : Business + User + BusinessMember

- **Date** : 2026-10-11
- **Statut** : Accepté
- **Décision** :
  - Table de jointure `business_members` avec contrainte unique `(business_id, user_id)`
  - FK `ON DELETE CASCADE`
  - Pas de `role` pour l'instant (prévu plus tard)
