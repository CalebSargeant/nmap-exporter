# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

Project: nmap-prometheus-exporter (Python + Prometheus + Nmap)

Key commands

- Local dev (Python)
  ```bash path=null start=null
  # One-time setup
  python3 -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  # Nmap binary is required for python-nmap
  # macOS: brew install nmap
  # Debian/Ubuntu: sudo apt-get install -y nmap
  ```
  ```bash path=null start=null
  # Run locally (short interval for dev)
  export TARGET_SOURCE=file
  export TARGET_FILE=./portscanip.nmap
  printf "1.1.1.1\n8.8.8.8\n" > ./portscanip.nmap
  SCAN_FREQUENCY=10 EXPORTER_PORT=9808 python exporter.py
  ```
  ```bash path=null start=null
  # Check metrics locally
  curl -s http://localhost:9808/metrics | head -n 20
  ```

- Docker Compose
  ```bash path=null start=null
  docker compose build
  docker compose up -d
  docker compose logs -f
  docker compose down
  ```

- Docker (without Compose)
  ```bash path=null start=null
  docker build -t nmap-exporter:dev .
  docker run --rm -p 9808:9808 --env-file .env nmap-exporter:dev
  ```

- Grafana dashboard (from README)
  ```bash path=null start=null
  DATASOURCE="YOUR_DS_NAME" ; sed "s/PROMETHEUS_DS_PLACEHOLDER/$DATASOURCE/g" dashboard_template.json > nmap-exporter-dashboard.json
  ```

- Tests/linting
  - No tests or lint configs are present in this repo.

Architecture and flow

- Entrypoint: exporter.py
  - Starts Prometheus HTTP server on EXPORTER_PORT, then enters an infinite scan loop.
  - Chooses target source by TARGET_SOURCE env: file | azure | aws.
  - Uses python-nmap’s PortScanner to scan resolved targets, then exposes metrics.
- Target discovery: modules/ip_fetcher.py
  - file: reads newline-delimited IPs from TARGET_FILE.
  - azure: takes AZURE_CREDENTIALS (JSON array of {AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID}); lists subscriptions via azure.mgmt.subscription and fetches public IPs from Azure REST API across all subscriptions.
  - aws: takes AWS_CREDENTIALS (JSON array of {AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_PROFILE_NAME, AWS_REGIONS:[...]}); for each region, describes Elastic IPs via boto3 and collects PublicIp values.
- Metrics emission: modules/prometheus_format.py
  - Gauge nmap_scan_results(host, protocol, name, product_detected) = port number per discovered service.
  - Info nmap_scan_stats(time_elapsed, uphosts, downhosts, totalhosts) for scan stats.
- Packaging: Dockerfile installs Python deps and nmap on python:3.11-alpine; docker-compose.yml exposes 9808 and reads .env.

Configuration (env vars)

- Core
  ```bash path=null start=null
  # Required depending on source
  TARGET_SOURCE=file|azure|aws
  SCAN_FREQUENCY=36000     # seconds; lower for dev
  EXPORTER_PORT=9808
  ```
- file source
  ```bash path=null start=null
  TARGET_FILE=/app/portscanip.nmap  # or a local path when running outside Docker
  ```
- azure source
  ```bash path=null start=null
  AZURE_CREDENTIALS='[{"AZURE_CLIENT_ID":"...","AZURE_CLIENT_SECRET":"...","AZURE_TENANT_ID":"..."}]'
  ```
- aws source
  ```bash path=null start=null
  AWS_CREDENTIALS='[{"AWS_ACCESS_KEY_ID":"...","AWS_SECRET_ACCESS_KEY":"...","AWS_PROFILE_NAME":"default","AWS_REGIONS":["eu-west-1"]}]'
  ```
- Multiple credentials: pass arrays with multiple objects in the same JSON env as above.

Prometheus integration

- Scrape config example
  ```yaml path=null start=null
  - job_name: nmap
    scrape_interval: 60s
    metrics_path: /metrics
    static_configs:
      - targets: ['<exporter-host>:9808']
  ```

Observability tips

- During development, set SCAN_FREQUENCY small (e.g., 10) to see rapid updates.
- Metrics of interest
  ```bash path=null start=null
  # Service results (labels: host, protocol, name, product_detected)
  nmap_scan_results
  # Scan stats (labels embedded as Info kv pairs)
  nmap_scan_stats
  ```

CI/CD

- .github/workflows/semantic-release.yaml triggers on pushes to main (and manual dispatch) using a reusable workflow; version bump type can be provided via the bump input.
