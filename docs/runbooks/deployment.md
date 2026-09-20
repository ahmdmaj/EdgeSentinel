# EdgeSentinel Production Deployment Runbook

This runbook details the exact steps required to deploy the EdgeSentinel stack onto a fresh Linux VM in a production environment. 
This deployment uses Docker Compose and Traefik for automatic SSL generation via Let's Encrypt.

## Prerequisites

1. A fresh Linux VM (Ubuntu 22.04 or 24.04 recommended) with a public IP address.
2. Two DNS `A` records pointing to your VM's public IP address:
   - `api.yourdomain.com` (Cloud API)
   - `dashboard.yourdomain.com` (Web Dashboard)
3. Docker and Docker Compose installed on the VM.

## Step-by-Step Deployment

### 1. Clone the Repository
Connect to your VM via SSH and clone the EdgeSentinel repository:

```bash
git clone https://github.com/ahmdmaj/EdgeSentinel.git
cd EdgeSentinel
```

### 2. Configure Production Secrets
Do not use the default `.env` or `.env.example` file in production. Instead, create a strictly separated `.env.production` file.

```bash
cp .env.production.example .env.production
```

Open `.env.production` using `nano` or `vim`:

```bash
nano .env.production
```

Fill in all the required variables:
- `DOMAIN_NAME`: Set this to your base domain (e.g., `yourdomain.com`).
- `ACME_EMAIL`: The email used for Let's Encrypt certificates.
- Generate strong, random passwords for `MYSQL_PASSWORD`, `MQTT_PASSWORD`, `JWT_SECRET`, etc.

**Critical Note:** You must manually generate and sync the MQTT password file using the Mosquitto utility. If you changed `MQTT_PASSWORD` in `.env.production`, run this command to update the `mosquitto.passwd` file:

```bash
docker run --rm -v "$(pwd)/infrastructure/mosquitto/config:/mosquitto/config" eclipse-mosquitto:2.0.18 sh -c "mosquitto_passwd -b -c /mosquitto/config/mosquitto.passwd edge_client YOUR_NEW_MQTT_PASSWORD"
```

### 3. Deploy the Stack
Launch the stack using both the base compose file and the production override file. The production override removes exposed host ports and introduces the Traefik reverse proxy.

```bash
# First, pull/build the images
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# Launch the stack in detached mode
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 4. Verification
Check the status of the containers. All containers should be `Up (healthy)`.

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

Monitor Traefik logs to ensure SSL certificates were provisioned successfully:

```bash
docker logs edgesentinel-traefik
```

### 5. Access the System
Your system is now live and secure!

- **Web Dashboard:** `https://dashboard.yourdomain.com`
- **Cloud API:** `https://api.yourdomain.com`

*Note: Internal services like MySQL, Prometheus, Grafana, and MQTT are fully firewalled by Docker and are only accessible inside the `edgesentinel-network`.*
