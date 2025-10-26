<h1 align="center">
  <img src="logo.png" alt="nmap-exporter Logo" width="150" />
</h1>

# nmap-exporter

**Description**:

This Docker application sets up the Nmap Prometheus Exporter, a versatile Python utility designed to scan and monitor network hosts and services using Nmap. It exposes the scan results and statistics in a Prometheus-compatible format. This exporter helps network administrators and DevOps teams gain insights into their network infrastructure, making it easier to detect changes, assess security, and maintain network health.

**Key Features**:

-   **Dockerized**: Easily deploy the Nmap Prometheus Exporter as a Docker container.
-   **Cross-Platform**: Platform-independent codebase ensuring compatibility with various operating systems.
-   **Automated Scanning**: Regularly scans a list of target IP addresses by dynamically fetching from Azure or a file.
-   **Prometheus Integration**: Exposes scan results and statistics as Prometheus metrics for easy monitoring and alerting.
-   **GeoIP Enrichment**: Optionally enrich scan results with network intelligence metadata (ISP, ASN, location, connection type).
-   **Customizable**: Easily configure the scan frequency, target file, and Prometheus port.
-   **Efficient**: Uses the Nmap library for efficient and comprehensive network scanning.
-   **Open Source**: Licensed under the MIT License for community contribution and collaboration.

## Prerequisites

Before running the Docker application, ensure you have the following prerequisites installed:

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Usage

1. **Clone this repository** to your local machine:

   ```bash
git clone https://github.com/your-username/nmap-exporter.git
   ```

2.  **Navigate to the project directory**:


`cd nmap-exporter`

3.  Create a `.env` file in the project directory with your environment variables. See the example in the `.env` section below.


4.  **Build the Docker image**:

`docker compose build`

5.  **Start the Docker container**:

`docker compose up -d`

6.  **Access Prometheus metrics** at `http://localhost:9808/metrics` (assuming you are running this on your local machine). Adjust the URL as needed based on your environment.

7.  To stop and remove the container, use the following command:


`docker compose down`


### Environment Variables (`.env` file)

Create a `.env` file in the project directory with the following variables:

If the list of IPs needs to be fetched from `azure` :
Replace the placeholders (`your_azure_client_id`, `your_azure_client_secret`, `your_azure_tenant_id`, and `your_azure_subscription_id`) with your actual Azure credentials.

```bash
TARGET_SOURCE=azure
AZURE_CREDENTIALS=[{"AZURE_CLIENT_ID":"your_azure_client_id", "AZURE_CLIENT_SECRET":"your_azure_client_secret", "AZURE_TENANT_ID":"your_azure_tenant_id"}]
SCAN_FREQUENCY=36000
EXPORTER_PORT=9808
```

If the list of IPs needs to be fetched from `aws` :
Replace the placeholders (`your_aws_access_key_id`, `your_aws_secret_key`, `your_azure_tenant_id`, `your_aws_profile_name` and `your_aws_region`) with your actual AWS credentials.

```bash
TARGET_SOURCE=aws
AWS_CREDENTIALS=[{"AWS_ACCESS_KEY_ID":"your_aws_access_key_id", "AWS_SECRET_ACCESS_KEY": "your_aws_secret_key", "AWS_PROFILE_NAME":"your_aws_profile_name", "AWS_REGIONS": ["your_aws_region"]}]
SCAN_FREQUENCY=36000
EXPORTER_PORT=9808
```
> **Note**: Multiple credentials whether AWS or Azure can be passed in the following format:
> **CREDENTIALS=[ { CREDENTIALS 1 }, { CREDENTIALS 2 } .... { CREDENTIALS N } ]**


If the list of IPs need to be fetched from  `file` :
Uncomment volume mount part from `docker-compose.yml` & replace `/path/to/your/portscanip.nmap`

Where `portscanip.nmap` is line terminated list of IP addresses


```bash
TARGET_SOURCE=file
TARGET_FILE=/app/portscanip.nmap
SCAN_FREQUENCY=36000
EXPORTER_PORT=9808
```

### GeoIP Enrichment (Optional)

The exporter can optionally enrich scan results with network intelligence metadata (ISP, ASN, location, connection type) from GeoIP APIs.

**Configuration:**

```bash
# Enable GeoIP enrichment
GEOIP_ENABLED=true

# GeoIP provider (currently supports: ipapi.co)
GEOIP_PROVIDER=ipapi.co

# Cache TTL in seconds (default: 86400 = 24 hours)
GEOIP_CACHE_TTL=86400

# Optional API token for the GeoIP provider
GEOIP_API_TOKEN=your_api_token_here
```

**Features:**
- Automatically enriches each scanned IP with ASN, ISP, country, city, and inferred connection type
- Caches results to avoid rate limits and redundant API calls
- Exposes enriched data as additional Prometheus metric labels
- Provides `/debug/geoip` endpoint for viewing cached enrichment data

**Connection Type Inference:**
The enricher automatically infers connection type based on ISP/ASN patterns:
- `mobile` - Mobile/LTE networks (Vodafone, T-Mobile, Verizon, etc.)
- `datacentre` - Cloud/hosting providers (AWS, Azure, Google Cloud, etc.)
- `fibre` - Fiber networks (FTTH, FTTP)
- `dsl` - DSL/ADSL/VDSL connections
- `unknown` - Unrecognized patterns

**Example enriched metric:**
```
nmap_scan_results_geoip{host="8.8.8.8",protocol="tcp",name="http",product_detected="",isp="Google LLC",asn="AS15169",country="US",city="Mountain View",connection_type="datacentre"} 80
```


## Adding Prometheus Target and Alert Rules

To monitor your `nmap-prometheus-exporter` instance effectively, you can configure Prometheus to scrape metrics from it and set up alert rules for potential issues. Here's how you can do it:

### Prometheus Target Configuration

1.  Edit your Prometheus configuration file, typically named `prometheus.yml`.

2.  Add a new job configuration under `scrape_configs` to specify the target to scrape metrics from your `nmap-prometheus-exporter` instance. Replace `<exporter-host>` with the hostname or IP address where your exporter is running and `<port>` with the configured port (default: 9808).

```yaml
    - job_name: nmap
      scrape_interval: 60s
      scrape_timeout: 30s
      metrics_path: "/metrics"
      static_configs:
      - targets: ['<exporter-host>:<port>']
        labels:
          cloud: CLOUD_NAME # Replace "CLOUD_NAME" with your cloud provider (aws, azure, gcp, or any other)
```

3.  Save the `prometheus.yml` file.

4.  Restart Prometheus to apply the changes.


### Alert Rules Configuration

To set up alert rules for your `nmap-prometheus-exporter`, follow these steps:

1.  Edit your Prometheus alerting rules file, typically named `alert.rules.yml`.

2.  Add your alerting rules to the file. Here's an example rule that alerts when the `nmap-exporter` service is down:


yamlCopy code
```yaml
`groups:
  - alert: awsNmapExporterDown
    expr: up{job="nmap"} == 0
    for: 1m
    labels:
      severity: Critical
      frequency: Daily
    annotations:
      summary: "Nmap Exporter is down (instance {{ $labels.instance_name }})"
      description: "Nmap Exporter is down\n VALUE = {{ $value }}\n for instance {{ $labels.instance_name }}"

  # Replace "CLOUD_NAME" with the one that was added with the target
  # Multiple alerts can men created for each cloud or ports
  - alert: Port22_CLOUD_NAME
    expr: nmap_scan_results{cloud="CLOUD_NAME"} == 22
    labels:
      severity: Critical
      frequency: Daily
    annotations:
      summary: "Port 22 is open to the world on an instance in CLOUD_NAME with IP address {{ $labels.host }}"
      description: "Port 22 is open to the world on an instance in "CLOUD_NAME" with IP address {{ $labels.host }}"
```

3.  Save the `alert.rules.yml` file.

4.  Reload Prometheus to apply the new alert rules.


With these configurations in place, Prometheus will scrape metrics from your `nmap-prometheus-exporter`, and alerting rules will trigger alerts based on defined conditions. Customize the alerting rules to fit your monitoring needs.

## Grafana Dashboard

A comprehensive Grafana dashboard is available to visualize all metrics collected by `nmap-exporter`. The dashboard provides insights into:

- **Network Health**: Scan duration, target count, success/failure rates
- **Security Status**: Open ports by host, port types distribution
- **GeoIP Intelligence**: Connection types, geographic distribution, ISP/ASN information
- **Scan Statistics**: Operational metrics and scan performance

### Dashboard Features

The dashboard includes the following panels:

1. **Overview Metrics**: Total targets, scan duration, successful/failed scans
2. **Scan Statistics**: Detailed scan information (time elapsed, up/down hosts)
3. **Port Analysis**: 
   - Open ports distribution by host (donut chart)
   - Port types distribution (donut chart)
   - Detailed port scan results table
4. **GeoIP Analysis** (when GeoIP enrichment is enabled):
   - Connection types distribution (mobile, datacentre, fibre, DSL)
   - Geographic distribution by country
   - Enriched results table with ISP, ASN, country, city information
5. **Time Series Graphs**:
   - Scan duration over time
   - Scan success/failure rate trends

### Importing the Dashboard

#### Method 1: Direct Import from File

1. **Download the Dashboard**: Get the dashboard JSON from the repository at `grafana-dashboards/nmap-exporter-dashboard.json`

2. **Access Grafana**: Log in to your Grafana instance

3. **Import Dashboard**:
   - Click on the "+" icon in the left sidebar
   - Select "Import dashboard"
   - Click "Upload JSON file" and select `nmap-exporter-dashboard.json`
   - Or copy and paste the JSON content directly

4. **Configure Data Source**:
   - Select your Prometheus data source from the dropdown
   - Click "Import"

5. **Select Cloud Filter** (optional):
   - Use the "Cloud" dropdown at the top of the dashboard to filter by cloud provider
   - Select "All" to view metrics from all sources

#### Method 2: Import from GitHub

You can also import the dashboard directly from the raw GitHub URL:

1. Navigate to **Dashboards** → **Import** in Grafana
2. Use this URL in the "Import via grafana.com" field:
   ```
   https://raw.githubusercontent.com/CalebSargeant/nmap-exporter/main/grafana-dashboards/nmap-exporter-dashboard.json
   ```
3. Click "Load"
4. Select your Prometheus data source
5. Click "Import"

### Dashboard Variables

The dashboard uses the following variables:

- **DS_PROMETHEUS**: Automatically populated with your Prometheus datasource
- **cloud**: Filter to select which cloud provider's metrics to display (e.g., "aws", "azure", or "All")

### Customizing the Dashboard

After importing, you can customize the dashboard:

- Adjust time ranges using the time picker in the top-right
- Modify panel queries to focus on specific metrics
- Add additional panels for custom visualizations
- Set up alerts based on specific thresholds

### Metrics Reference

The dashboard visualizes the following Prometheus metrics:

- `nmap_scan_results` - Basic scan results (host, port, protocol, service, product)
- `nmap_scan_results_geoip` - GeoIP-enriched results (includes ISP, ASN, country, city, connection type)
- `nmap_scan_stats_info` - Scan statistics (time elapsed, up/down hosts)
- `nmap_target_count` - Number of targets discovered
- `nmap_scan_duration_seconds` - Duration of the last scan
- `nmap_successful_scans_total` - Total successful scan batches (counter)
- `nmap_failed_scans_total` - Total failed scan batches (counter)

## License

This project is licensed under the MIT License - see the [LICENSE](https://chat.openai.com/c/LICENSE) file for details.

## Acknowledgments

-   [Nmap](https://nmap.org/) - The network scanner used for scanning.
-   [Prometheus](https://prometheus.io/) - The monitoring and alerting toolkit.
-   [Docker](https://www.docker.com/) - The containerization platform.
-   [Docker Compose](https://docs.docker.com/compose/) - The tool for defining and running multi-container Docker applications.
-   [Grafana](https://grafana.com/) - The visualization and monitoring platform.

**Logo Credit:** The logo design used in this project was crafted with the assistance of [LogoMakr.com/app](https://logomakr.com/app). We appreciate the creative support from LogoMakr in shaping our visual identity.


<!-- BEGIN_TF_DOCS -->
## Requirements

No requirements.

## Providers

No providers.

## Modules

No modules.

## Resources

No resources.

## Inputs

No inputs.

## Outputs

No outputs.
<!-- END_TF_DOCS -->
