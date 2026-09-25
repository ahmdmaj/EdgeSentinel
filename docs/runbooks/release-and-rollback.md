# EdgeSentinel Release & Rollback Runbook

This document outlines the standard operating procedures (SOP) for deploying immutable container artifacts to the EdgeSentinel production environment, as well as the immediate rollback procedures in case of a critical failure.

All images are automatically built, scanned via Trivy, and pushed to the GitHub Container Registry (GHCR) upon pushing to `main` or creating a Git tag (e.g., `v1.0.0`).

## 1. Prerequisites

Ensure you are SSH'd into the production VM and are in the repository directory.
```bash
cd /opt/edgesentinel
```

Ensure your `.env.production` file is up-to-date and your GitHub username is exported so Docker can pull the images.
```bash
export GH_USERNAME="ahmdmaj"
```

---

## 2. Standard Deployment Procedure

To deploy a new release, you simply pull the updated configurations and specify the immutable tag (either the Git SHA or the Release Tag).

**Step 1: Pull the latest configurations**
```bash
git pull origin main
```

**Step 2: Export the desired Image Tag**
```bash
# E.g., deploying version 1.0.0
export IMAGE_TAG="v1.0.0"

# Or deploying a specific commit SHA (found in GHCR)
export IMAGE_TAG="sha-a1b2c3d"
```

**Step 3: Authenticate to GHCR (first time only)**
You must authenticate to the GitHub Container Registry using a Personal Access Token (PAT) with `read:packages` scope.
```bash
echo $CR_PAT | docker login ghcr.io -u $GH_USERNAME --password-stdin
```

**Step 4: Pull and Apply the new containers**
```bash
# This forces Docker to pull the images and recreate the containers.
# The 'build: null' override prevents it from trying to build locally.
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

**Step 5: Verify Deployment**
```bash
docker compose ps
# Ensure cloud-api, edge-service, and web are running and healthy.
```

---

## 3. Immediate Rollback Procedure

If a deployed version causes a critical issue (e.g., an unhandled exception loops, memory leaks, or a bad migration), we rollback by instantly downgrading the image tag to the last known-good state.

**Step 1: Identify the previous known-good tag**
Find the previous `vX.X.X` tag or commit SHA that was working securely.
```bash
# Set the tag to the working version
export IMAGE_TAG="v0.9.0"
```

**Step 2: Apply the Rollback**
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

**Why this works instantly:**
Because we are using immutable tags, the host VM already has the previous `v0.9.0` image layers cached locally. Docker simply stops the broken containers and instantly starts the old ones without waiting for a rebuild or a fresh download.

## 4. Security Notes
- The CI pipeline enforces Trivy security scans before pushing any image. If `CRITICAL` or `HIGH` vulnerabilities are found, the pipeline fails and the image is never pushed to GHCR.
- Production environments *never* use the `:latest` tag, as it makes rollbacks non-deterministic. Always pin to an exact tag or commit SHA.
