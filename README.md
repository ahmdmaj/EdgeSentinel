# EdgeSentinel Monorepo Architecture

Welcome to the **EdgeSentinel** project! This platform is an "offline-first edge-cloud anomaly detection system." Because a system like this has many moving parts (cloud servers, local edge devices, databases, and IoT simulators), we are using a **Monorepo** structure. 

A monorepo means all the different parts of the system live in this single repository. Here is a breakdown of exactly why every folder and file exists in this project:

---

## 📂 `apps/`
This folder holds our primary, cloud-hosted applications.
* **`apps/api/` (Cloud API):** This is the central brain in the cloud. It's a Node.js (Fastify) server that receives aggregated data from all the remote edge nodes, stores it in the Postgres database, and serves it to the web dashboard.
* **`apps/web/` (Frontend Dashboard):** *(Coming soon)* This will be our Next.js React application. It is the user interface where administrators will log in to view charts, anomalies, and monitor the health of all edge devices.

## 📂 `services/`
This folder holds our backend microservices and edge-deployed components.
* **`services/edge/` (Edge Node):** This is the Python service designed to be deployed physically on-site (the "edge"). It listens to local machines, uses Machine Learning to detect anomalies immediately, and stores data locally if the internet goes down. 
* **`services/simulator/` (IoT Simulator):** Since we don't have real factory machines plugged into our laptops, this Python script generates fake temperature/vibration data so we can test our software.

## 📂 `infrastructure/`
This folder contains the configuration for our 3rd-party tools and databases.
* **`infrastructure/mosquitto/`:** Holds the configuration for our Eclipse Mosquitto MQTT Broker. MQTT is the lightweight messaging protocol our simulator uses to send data to the edge node.

## 📂 `packages/`
*(Empty for now)* This folder is for shared code. For example, if both the `apps/web` and `apps/api` need to use the exact same TypeScript types or utility functions, we put them here so we don't have to write the code twice.

## 📂 `ml/`
*(Empty for now)* A dedicated workspace for Data Scientists. This is where Jupyter Notebooks, training data, and experiments will live before the final Machine Learning models are exported to the `services/edge/` node.

## 📂 `docs/`
*(Empty for now)* Where detailed project documentation, API specs, and architecture diagrams will go.

---

## 📄 Root Files
* **`docker-compose.yml`:** The orchestration file. When you run `docker compose up`, this file tells Docker how to boot up the API, the Edge Node, the Simulator, the Postgres database, and the Mosquitto broker, and how to connect them all together on a shared virtual network.
* **`package.json`:** Since we are using an NPM Workspace, this file tells the package manager how to link `apps/` and `packages/` together.
* **`.env` & `.env.example`:** Stores our secret passwords, database connection strings, and network ports. We use `.env.example` as a safe template to commit to version control, while `.env` stays hidden.
* **`.gitignore`:** Tells Git which files (like heavy `node_modules/` or secret `.env` files) to ignore and NEVER upload to GitHub.
