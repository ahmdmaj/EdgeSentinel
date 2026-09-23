# EdgeSentinel Disaster Recovery Runbook

This runbook defines the recovery procedures for catastrophic failures in the EdgeSentinel production stack. All steps assume a single-VM Docker Compose deployment.

---

## Recovery Objectives

| Objective | Target | Rationale |
| :--- | :--- | :--- |
| **RPO (Recovery Point Objective)** | **≤ 24 hours of cloud data** | Daily `backup-db.sh` cron means at most one day of MySQL telemetry is lost in a catastrophic disk failure. **0 data loss** for temporary network drops: the Edge Node Outbox buffers all events locally and retransmits on recovery. |
| **RTO (Recovery Time Objective)** | **< 15 minutes** | Time to: clone repo → populate `.env` → run `restore-db.sh` → `docker compose up -d`. |

---

## Failure Matrix

| Failure Scenario | System Behavior | Edge Impact | Resolution |
| :--- | :--- | :--- | :--- |
| **Cloud API down** | `GET /api/v1/telemetry` returns 503. Web dashboard shows stale data. | Edge SyncWorker applies exponential backoff and buffers all new events in SQLite outbox. **Zero data loss.** | `docker compose restart cloud-api` |
| **MySQL down** | Cloud API fails its healthcheck and stops accepting requests. | Same as above — Edge buffers locally. | `docker compose restart mysql`. If corrupt: run `restore-db.sh`. |
| **Edge Node restart** | Edge Node reconnects to MQTT broker automatically. Outbox worker resumes. | Unsent events in SQLite are preserved across restarts. **Zero data loss.** | Automatic — no manual intervention required. |
| **Complete Cloud outage** | All cloud services (API, MySQL, Web) are unreachable. | Edge stores all telemetry locally. When cloud recovers, SyncWorker replays the full backlog in FIFO order. **Zero data loss for up to SQLite disk capacity.** | Restore from latest backup, then `docker compose up -d`. |

---

## Incident Procedures

### Procedure 1: Create a Database Snapshot

Run this before any risky operations (schema migrations, deployments, etc.):

```bash
bash infrastructure/scripts/backup-db.sh
```

Expected output:
```
Starting backup of 'edgesentinel' database...
Destination: ./backups/edgesentinel_backup_20260922_020000.sql
Backup completed successfully: ./backups/edgesentinel_backup_20260922_020000.sql
Size: 2.1M
Old backups (>7 days) pruned.
```

---

### Procedure 2: Restore from Backup (Catastrophic Data Loss)

> [!CAUTION]
> This procedure will **completely overwrite** the current database. Ensure the backup file is valid before proceeding.

**Step 1:** Identify the most recent backup file.
```bash
ls -lht ./backups/
```

**Step 2:** Run the restore script, providing the backup file path.
```bash
bash infrastructure/scripts/restore-db.sh ./backups/edgesentinel_backup_YYYYMMDD_HHMMSS.sql
```

**Step 3:** When prompted, type `yes` to confirm.

**Step 4:** After restore completes, restart the Cloud API so Prisma reconnects cleanly.
```bash
docker compose restart cloud-api
```

**Step 5:** Verify data is present.
```bash
# Check row count in telemetry table
docker exec edgesentinel-mysql mysql -u admin -psecret edgesentinel \
  -e "SELECT COUNT(*) AS total_events FROM telemetry;"
```

**Step 6:** Open Grafana at `http://localhost:3002` and verify dashboards show historical data.

---

### Procedure 3: Schedule Automated Daily Backups (Linux/WSL)

Add the following to your crontab (`crontab -e`) to run `backup-db.sh` every day at 2:00 AM:

```cron
0 2 * * * /bin/bash /path/to/EdgeSentinel/infrastructure/scripts/backup-db.sh >> /var/log/edgesentinel-backup.log 2>&1
```

---

### Procedure 4: Full Stack Recovery on a Fresh VM

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ahmdmaj/EdgeSentinel.git && cd EdgeSentinel
   ```

2. **Restore environment secrets:**
   ```bash
   cp .env.production.example .env.production
   nano .env.production  # Fill in all values
   ```

3. **Copy the backup file** to the new VM's `./backups/` directory (via `scp` or cloud storage).

4. **Start the database first** and wait for it to be healthy:
   ```bash
   docker compose up -d mysql
   docker compose ps  # Wait until mysql shows (healthy)
   ```

5. **Run the restore script:**
   ```bash
   bash infrastructure/scripts/restore-db.sh ./backups/edgesentinel_backup_YYYYMMDD_HHMMSS.sql
   ```

6. **Bring up the rest of the stack:**
   ```bash
   docker compose up -d
   ```

7. **Verify all containers are healthy:**
   ```bash
   docker compose ps
   ```

**Total estimated RTO: < 15 minutes** on a provisioned VM with a pre-configured `.env` file.
