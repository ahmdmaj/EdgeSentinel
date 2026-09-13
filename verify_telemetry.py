import sqlite3

conn = sqlite3.connect("apps/api/prisma/dev.db")
cursor = conn.cursor()
cursor.execute("SELECT id, event_id, device_id, temperature, humidity, vibration, pressure, machine_state, created_at FROM telemetry WHERE event_id = 'evt-outage-test-002'")
row = cursor.fetchone()

print("================ PRISMA DATABASE QUERY RESULT ================")
if row:
    print(f"ID:            {row[0]}")
    print(f"Event ID:      {row[1]}")
    print(f"Device ID:     {row[2]}")
    print(f"Temperature:   {row[3]}")
    print(f"Humidity:      {row[4]}")
    print(f"Vibration:     {row[5]}")
    print(f"Pressure:      {row[6]}")
    print(f"Machine State: {row[7]}")
    print(f"Created At:    {row[8]}")
    print("STATUS: VERIFIED PERSISTED IN DATABASE!")
else:
    print("Record evt-outage-test-002 not found!")

# Also print total telemetry count in database
cursor.execute("SELECT count(*) FROM telemetry")
total = cursor.fetchone()[0]
print(f"Total Telemetry Records in Cloud Database: {total}")
conn.close()
