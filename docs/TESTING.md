# Testing

## Prérequis

```bash
uv sync --dev
```

## Tests unitaires (sans DB)

```bash
uv run pytest tests/ -v
```

### Résultat attendu

```
11+ tests PASSED  (health + business + user + business_member)
```

## Migrations (avec PostgreSQL via Docker)

```bash
# 1. Démarrer Postgres
docker run --name whatsapp-pg \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=whatsapp_agent \
  -p 5432:5432 \
  -d postgres:16

# 2. .env
cp .env.example .env
# DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/whatsapp_agent

# 3. Migrations
uv run alembic upgrade head

# 4. Vérifier
uv run alembic current
```

## Notes

- `env.py` charge automatiquement le `.env` via `python-dotenv`.
- Les tests des modèles n'ont **pas besoin** de PostgreSQL.
