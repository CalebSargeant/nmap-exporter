#!/usr/bin/env python3

from __future__ import absolute_import
import prometheus_client
import logging
import json
from typing import Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create Prometheus metrics without clearing them
metric_results = prometheus_client.Gauge("nmap_scan_results",
                                         "Holds the scanned result",
                                         ["host",
                                          "target",
                                          "protocol",
                                          "name",
                                          "product_detected"])

# GeoIP-enriched metric with additional labels
metric_results_geoip = prometheus_client.Gauge("nmap_scan_results_geoip",
                                               "Holds the scanned result with GeoIP metadata",
                                               ["host",
                                                "target",
                                                "protocol",
                                                "name",
                                                "product_detected",
                                                "isp",
                                                "asn",
                                                "country",
                                                "city",
                                                "connection_type"])

metric_info = prometheus_client.Info("nmap_scan_stats",
                                     "Holds details about the scan")

# Observability metrics
metric_target_count = prometheus_client.Gauge("nmap_target_count",
                                              "Number of targets discovered for scanning")
metric_scan_duration = prometheus_client.Gauge("nmap_scan_duration_seconds",
                                               "Duration of the last scan in seconds")
metric_failed_scans = prometheus_client.Counter("nmap_failed_scans_total",
                                                "Total number of failed scan batches")
metric_successful_scans = prometheus_client.Counter("nmap_successful_scans_total",
                                                    "Total number of successful scan batches")

# Exposes results of the scan in Prometheus format
def expose_nmap_scan_results(nm, geoip_data: Optional[Dict[str, Dict]] = None, hostname_map: Optional[Dict[str, str]] = None):
    """
    Expose Nmap scan results as Prometheus metrics.

    Args:
        nm: Nmap PortScanner instance with scan results
        geoip_data: Optional dictionary mapping IP -> GeoIP metadata
        hostname_map: Optional dictionary mapping IP -> original target hostname
    """
    list_scanned_items = []

    for line in str(nm.csv()).splitlines():
        list_scanned_items.append(line)

    for line in list_scanned_items[1:]:
        host, _, _, prot, port, name, _, prod, *_ = line.split(";")

        # Get original target hostname if available
        target = hostname_map.get(host, host) if hostname_map else host

        # Always expose the basic metric
        metric_results.labels(host, target, prot, name, prod).set(float(port))

        # If GeoIP data is available, also expose enriched metric
        if geoip_data and host in geoip_data:
            geo = geoip_data[host]
            metric_results_geoip.labels(
                host=host,
                target=target,
                protocol=prot,
                name=name,
                product_detected=prod,
                isp=geo.get("isp", ""),
                asn=geo.get("asn", ""),
                country=geo.get("country", ""),
                city=geo.get("city", ""),
                connection_type=geo.get("connection_type", "unknown")
            ).set(float(port))

# Exposes stats of the scan in Prometheus format
def expose_nmap_scan_stats(nm):
    scanstats = nm.scanstats()
    metric_info.info({"time_elapsed": scanstats["elapsed"],
                      "uphosts": scanstats["uphosts"],
                      "downhosts": scanstats["downhosts"],
                      "totalhosts": scanstats["totalhosts"]})

def start_prometheus_server(exporter_port, geoip_enricher=None):
    """
    Start Prometheus HTTP server with optional GeoIP debug endpoint.

    Args:
        exporter_port: Port to start the server on
        geoip_enricher: Optional GeoIPEnricher instance for debug endpoint
    """
    # Store reference for use in handler
    global _geoip_enricher
    _geoip_enricher = geoip_enricher

    if geoip_enricher:
        # Start server with custom handler for debug endpoint
        from http.server import BaseHTTPRequestHandler
        from prometheus_client import MetricsHandler
        import threading
        from http.server import HTTPServer

        class CustomHandler(MetricsHandler):
            def do_GET(self):
                if self.path == '/debug/geoip':
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()

                    cache_data = _geoip_enricher.get_cached_data()
                    cache_stats = _geoip_enricher.get_cache_stats()

                    response = {
                        "stats": cache_stats,
                        "cached_data": cache_data
                    }

                    self.wfile.write(json.dumps(response, indent=2).encode('utf-8'))
                else:
                    # Handle metrics endpoint normally
                    super().do_GET()

        server = HTTPServer(('', exporter_port), CustomHandler)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        print(f"Prometheus HTTP server started on port {exporter_port} (with /debug/geoip endpoint)")
    else:
        prometheus_client.start_http_server(exporter_port)
        print(f"Prometheus HTTP server started on port {exporter_port}")

# Global reference for GeoIP enricher (used by HTTP handler)
_geoip_enricher = None

# Observability metric setters
def set_target_count(count):
    metric_target_count.set(count)

def set_scan_duration(duration):
    metric_scan_duration.set(duration)

def increment_failed_scans():
    metric_failed_scans.inc()

def increment_successful_scans():
    metric_successful_scans.inc()
