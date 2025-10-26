# Grafana Dashboards for nmap-exporter

This directory contains Grafana dashboard configurations for visualizing metrics from nmap-exporter.

## Available Dashboards

### nmap-exporter-dashboard.json

A comprehensive dashboard providing complete visibility into network scanning operations, security status, and GeoIP intelligence.

**Dashboard UID**: `nmap-exporter`

**Panels Included**:

1. **Overview Metrics** (Row 1)
   - Total Targets (stat panel)
   - Last Scan Duration (stat panel with thresholds)
   - Successful Scans (counter stat)
   - Failed Scans (counter stat with alert threshold)

2. **Scan Statistics** (Row 2)
   - Detailed scan info table (time elapsed, up/down hosts, total hosts)

3. **Port Analysis** (Row 3)
   - Open Ports by Host (donut chart)
   - Port Types Distribution (donut chart)

4. **Detailed Results** (Row 4)
   - Port Scan Results table (filterable, sortable)

5. **GeoIP Analysis** (Rows 5-6, when GeoIP is enabled)
   - Connection Types Distribution (mobile, datacentre, fibre, DSL)
   - Geographic Distribution by Country
   - GeoIP Enriched Results table (with ISP, ASN, city, country)

6. **Time Series Analysis** (Rows 7-8)
   - Scan Duration Over Time (line graph)
   - Scan Success/Failure Rate (multi-line graph)

**Variables**:
- `DS_PROMETHEUS`: Datasource selector (automatically configured on import)
- `cloud`: Cloud provider filter (aws, azure, or All)

**Refresh Rate**: 30 seconds (configurable)

**Time Range**: Last 6 hours (default, adjustable)

## Quick Start

### Import via Grafana UI

1. Navigate to your Grafana instance
2. Click "+" → "Import dashboard"
3. Upload `nmap-exporter-dashboard.json` or paste its contents
4. Select your Prometheus datasource
5. Click "Import"

### Import via Grafana API

```bash
# Set your Grafana URL and API key
GRAFANA_URL="http://localhost:3000"
GRAFANA_API_KEY="your-api-key-here"

# Import the dashboard
curl -X POST "$GRAFANA_URL/api/dashboards/db" \
  -H "Authorization: Bearer $GRAFANA_API_KEY" \
  -H "Content-Type: application/json" \
  -d @nmap-exporter-dashboard.json
```

### Import from GitHub (Direct URL)

In Grafana's Import screen, use this URL:
```
https://raw.githubusercontent.com/CalebSargeant/nmap-exporter/main/grafana-dashboards/nmap-exporter-dashboard.json
```

## Prerequisites

To use these dashboards effectively, ensure:

1. **Prometheus is configured** to scrape nmap-exporter metrics
   - Default endpoint: `http://<exporter-host>:9808/metrics`
   - Recommended scrape interval: 60s

2. **Prometheus datasource is configured** in Grafana
   - Add Prometheus as a datasource in Grafana
   - Point it to your Prometheus instance

3. **nmap-exporter is running** and generating metrics
   - Verify metrics are available at `/metrics` endpoint
   - Check that scans are completing successfully

## Dashboard Customization

### Modify Time Ranges

Change the default time range in the dashboard JSON:
```json
"time": {
  "from": "now-6h",  // Change this
  "to": "now"
}
```

### Add Custom Panels

You can extend the dashboard by:
- Adding new panels for specific ports (e.g., SSH port 22 monitoring)
- Creating alerts for critical security findings
- Adding annotations for deployment events
- Customizing colors and thresholds

### Filter by Specific Hosts

Add a new variable to filter by specific hosts:
1. Edit dashboard settings
2. Add new variable: `label_values(nmap_scan_results, host)`
3. Modify panel queries to include: `{host=~"$host"}`

## Metrics Used

The dashboard queries the following Prometheus metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `nmap_scan_results` | Gauge | Basic scan results (port, service, product) |
| `nmap_scan_results_geoip` | Gauge | GeoIP-enriched results |
| `nmap_scan_stats_info` | Info | Scan statistics and metadata |
| `nmap_target_count` | Gauge | Number of discovered targets |
| `nmap_scan_duration_seconds` | Gauge | Last scan duration |
| `nmap_successful_scans_total` | Counter | Successful scan batches |
| `nmap_failed_scans_total` | Counter | Failed scan batches |

## Troubleshooting

### No Data Displayed

1. **Check Prometheus datasource**: Verify it's correctly configured
2. **Verify metrics**: Visit `http://<exporter>:9808/metrics` directly
3. **Check time range**: Ensure it covers when scans occurred
4. **Verify cloud label**: If using cloud filter, ensure label matches

### GeoIP Panels Empty

GeoIP panels require:
- `GEOIP_ENABLED=true` in nmap-exporter configuration
- Successful GeoIP API calls (check exporter logs)
- `nmap_scan_results_geoip` metric populated

### Permission Issues

Ensure your Grafana user has:
- Permission to create/import dashboards
- Access to the Prometheus datasource

## Support

For issues or feature requests:
- GitHub Issues: https://github.com/CalebSargeant/nmap-exporter/issues
- Documentation: https://github.com/CalebSargeant/nmap-exporter/blob/main/README.md

## License

These dashboards are provided under the same MIT License as the nmap-exporter project.
