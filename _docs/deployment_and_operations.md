# Deployment, Migration & Operations Runbook

## 1. Local Development & Verification

### Backend Setup & Automated Tests
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate  |  Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt

# Run unit, financial math, and tenant-isolation tests
pytest -v
```

### Frontend Type-Check & Production Build
```bash
cd frontend
npm install
npm run build   # Runs vue-tsc && vite build
```

### Local Full-Stack Docker Compose
```bash
docker compose up --build -d
# Apply Alembic migrations
docker compose exec backend alembic upgrade head
```

---

## 2. Database Migrations & Rollback (`alembic`)

All schema changes are tracked in `backend/alembic/versions/`.

- **Check current migration version:**
  ```bash
  alembic current
  ```
- **Apply all pending migrations:**
  ```bash
  alembic upgrade head
  ```
- **Create a new migration after editing SQLAlchemy models:**
  ```bash
  alembic revision --autogenerate -m "describe_schema_change"
  ```
- **Rollback the most recent migration:**
  ```bash
  alembic downgrade -1
  ```
- **Full rollback of initial baseline (`0001_initial_schema`):**
  ```bash
  alembic downgrade base
  ```

---

## 3. Production Deployment (Hetzner VPS + Traefik + Let's Encrypt)

1. **Provision secrets:**
   ```bash
   cp .env.prod.example .env.prod
   ```
   Edit `.env.prod` and set:
   - `APP_DOMAIN` (DNS `A` record pointing to your VPS IP)
   - `ACME_EMAIL` (Let's Encrypt notifications)
   - `SECRET_KEY` (`openssl rand -hex 32`)
   - `POSTGRES_PASSWORD` (strong generated password)
   - `BACKEND_CORS_ORIGINS=["https://wealth.example.com"]`
   - `ALLOW_PUBLIC_REGISTRATION=False` (the **first** user to register automatically becomes owner/superuser; subsequent public registrations are blocked with HTTP `403` while `ALLOW_PUBLIC_REGISTRATION=False`).

2. **Build and launch production stack:**
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
   ```
   - `backend` automatically executes `alembic upgrade head` before starting `uvicorn` with 2 workers.
   - `postgres` and `redis` live strictly on `internal_net` with zero public host ports exposed.
   - `traefik` terminates HTTPS with automatic HTTP-to-HTTPS redirect and Let's Encrypt TLS certificates.
   - Startup enforces `Settings.validate_production_security()` and aborts boot if development placeholder secrets are left active.

---

## 4. Backups & Disaster Recovery Drill

### Daily Automated Backup (Cron Example)
Add to host crontab (`crontab -e`) for 02:30 UTC daily backups:
```cron
30 2 * * * cd /opt/finance-tracker && ./scripts/backup_postgres.sh /opt/finance-tracker/backups 30 >> /var/log/wealth_backup.log 2>&1
```

### Verify Backup Recoverability (Non-Destructive)
```bash
./scripts/restore_postgres.sh ./backups/finance_tracker_YYYYMMDDTHHMMSSZ.sql.gz --verify-sandbox
```
This restores the compressed dump into a temporary `restore_verify_*` database, verifies restored table count, and cleans up the temporary database afterward.

### Full Restore (Disaster Recovery)
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod stop backend
./scripts/restore_postgres.sh ./backups/finance_tracker_YYYYMMDDTHHMMSSZ.sql.gz
docker compose -f docker-compose.prod.yml --env-file .env.prod start backend
```

