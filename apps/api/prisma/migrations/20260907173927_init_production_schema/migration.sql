-- CreateTable
CREATE TABLE "users" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "email" TEXT NOT NULL,
    "password_hash" TEXT NOT NULL,
    "role" TEXT NOT NULL DEFAULT 'VIEWER',
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "devices" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "device_id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "telemetry" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "event_id" TEXT NOT NULL,
    "device_id" TEXT NOT NULL,
    "temperature" REAL NOT NULL,
    "humidity" REAL NOT NULL,
    "vibration" REAL NOT NULL,
    "pressure" REAL NOT NULL,
    "machine_state" TEXT NOT NULL,
    "timestamp" DATETIME NOT NULL,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "telemetry_device_id_fkey" FOREIGN KEY ("device_id") REFERENCES "devices" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "anomaly_events" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "telemetry_id" TEXT NOT NULL,
    "severity" TEXT NOT NULL,
    "score" REAL NOT NULL,
    "decision" TEXT NOT NULL,
    "model_version" TEXT NOT NULL,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "anomaly_events_telemetry_id_fkey" FOREIGN KEY ("telemetry_id") REFERENCES "telemetry" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- CreateIndex
CREATE UNIQUE INDEX "devices_device_id_key" ON "devices"("device_id");

-- CreateIndex
CREATE UNIQUE INDEX "telemetry_event_id_key" ON "telemetry"("event_id");

-- CreateIndex
CREATE INDEX "telemetry_device_id_idx" ON "telemetry"("device_id");

-- CreateIndex
CREATE INDEX "anomaly_events_telemetry_id_idx" ON "anomaly_events"("telemetry_id");
