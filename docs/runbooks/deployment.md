# EdgeSentinel Production Deployment Runbook

This runbook details the exact steps required to deploy the EdgeSentinel stack in a strictly isolated environment. 
This deployment uses Docker Compose and Nginx as a reverse proxy, terminating SSL locally using a self-signed certificate.

## Prerequisites

1. A machine with Docker and Docker Compose installed.
2. Bash (or Git Bash on Windows) to run the SSL generation script.

## Step-by-Step Deployment

### 1. Clone the Repository
Connect to your machine and clone the EdgeSentinel repository:

```bash
git clone https://github.com/ahmdmaj/EdgeSentinel.git
cd EdgeSentinel
```

### 2. Generate Local SSL Certificates
Run the provided bash script to generate the self-signed certificates that Nginx will use.

```bash
bash infrastructure/nginx/generate-ssl.sh
```

This will create `cert.pem` and `key.pem` inside the `infrastructure/nginx/ssl` directory.

### 3. Configure Production Secrets
Do not use the default `.env` or `.env.example` file in production. Instead, create a strictly separated `.env.production` file.

```bash
cp .env.production.example .env.production
```

Open `.env.production` using your text editor and fill in all the required variables:
- Generate strong, random passwords for `MYSQL_PASSWORD`, `MQTT_PASSWORD`, `JWT_SECRET`, etc.

**Critical Note:** You must manually generate and sync the MQTT password file using the Mosquitto utility. If you changed `MQTT_PASSWORD` in `.env.production`, run this command to update the `mosquitto.passwd` file:

```bash
docker run --rm -v "$(pwd)/infrastructure/mosquitto/config:/mosquitto/config" eclipse-mosquitto:2.0.18 sh -c "mosquitto_passwd -b -c /mosquitto/config/mosquitto.passwd edge_client YOUR_NEW_MQTT_PASSWORD"
```

### 4. Deploy the Stack
Launch the stack using both the base compose file and the production override file. The production override removes exposed host ports and introduces the Nginx reverse proxy.

```bash
# First, pull/build the images
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# Launch the stack in detached mode
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 5. Verification
Check the status of the containers. All containers should be `Up`.

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

Monitor Nginx logs to ensure it booted and found the SSL certificates successfully:

```bash
docker logs edgesentinel-nginx
```

### 6. Access the System
Your system is now live and isolated!

- **Web Dashboard:** `https://localhost`
- **Cloud API:** `https://localhost/api/`

*Note: Your browser will show a "Not Secure" warning because the certificate is self-signed. This is expected for localhost development. Click "Advanced" -> "Proceed to localhost" to view the dashboard.*

*Note: Internal services like MySQL, Prometheus, Grafana, Cloud API, Web, and MQTT are fully firewalled by Docker and are only accessible inside the `edgesentinel-network`.*
