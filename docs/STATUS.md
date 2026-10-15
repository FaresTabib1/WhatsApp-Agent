# Status

## Phase 1 — Squelette backend

| Tâche | Description | Statut |
|-------|-------------|--------|
| 1/7 | Squelette FastAPI + endpoint `/health` + tests | ✅ Fait |

## Phase 2 — Données

| Tâche | Description | Statut |
|-------|-------------|--------|
| 1/4 | Modèle Business + migration Alembic | ✅ Fait |
| 2/4 | Modèle User + BusinessMember + migration | ✅ Fait |
| 3/4 | Session async SQLAlchemy + singleton `get_db` | ✅ Fait |
| 4/4 | Endpoints `/businesses` (POST, GET) + schémas Pydantic | ✅ Fait |

## Dernière mise à jour

- **Date** : 2026-10-12
- **Contenu livré** :
  - Session async SQLAlchemy + fabrique singleton + dépendance `get_db`
  - Schémas Pydantic `BusinessCreate`, `BusinessRead`
  - Endpoints `POST /businesses`, `GET /businesses/{business_id}`
  - Tests unitaires et d'API (43 tests au total)
