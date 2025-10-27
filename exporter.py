#!/usr/bin/env python3

from __future__ import absolute_import
import time
import sys
import os
import json
import nmap
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from modules.ip_fetcher import fetch_azure_ips, fetch_ips_from_file, fetch_aws_ips
from modules.prometheus_format import (
    expose_nmap_scan_results,
    expose_nmap_scan_stats,
    start_prometheus_server,
    set_target_count,
    set_scan_duration,
    increment_failed_scans,
    increment_successful_scans
)
from modules.geoip_enricher import GeoIPEnricher

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Scan a batch of targets
def scan_batch(batch_targets, nm, nmap_ports, nmap_args):
    """Scan a batch of targets and return results"""
    targets_str = " ".join(batch_targets)
    logger.info(f"Scanning batch of {len(batch_targets)} targets")
    try:
        nm_instance = nmap.PortScanner()
        nm_instance.scan(hosts=targets_str, ports=nmap_ports if nmap_ports else None, arguments=nmap_args)
        return nm_instance, None
    except Exception as e:
        logger.error(f"Batch scan failed: {str(e)}")
        return None, str(e)


# Main function
def main():
    try:
        # Print logo
        with open('ascii_logo.txt', 'r') as file:
            # Read and print the content
            content = file.read()
            print(content)

        nm = nmap.PortScanner()

        # Initialize GeoIP enricher if enabled
        geoip_enabled = os.getenv('GEOIP_ENABLED', 'false').lower() == 'true'
        geoip_enricher = None

        if geoip_enabled:
            geoip_provider = os.getenv('GEOIP_PROVIDER', 'ipapi.co')
            geoip_cache_ttl = int(os.getenv('GEOIP_CACHE_TTL', '86400'))  # Default 24 hours
            geoip_api_token = os.getenv('GEOIP_API_TOKEN')

            geoip_enricher = GeoIPEnricher(
                provider=geoip_provider,
                cache_ttl=geoip_cache_ttl,
                api_token=geoip_api_token
            )
            logger.info("GeoIP enrichment enabled")
        else:
            logger.info("GeoIP enrichment disabled")

        while True:
            # Fetch targets based on the selected source
            target_source = os.getenv('TARGET_SOURCE', 'file')

            if target_source == "file":
                required_env_vars = ['TARGET_FILE']
                missing_vars = [var for var in required_env_vars if os.getenv(var) is None]

                if missing_vars:
                    error_message = f"The following environment variables are missing: {', '.join(missing_vars)}"
                    raise EnvironmentError(error_message)
                else:
                    target_file = os.getenv('TARGET_FILE', '/app/portscanip.nmap')
                    targets_list = fetch_ips_from_file(target_file)
                    # dedupe, drop empties and join as space-separated hosts
                    targets = " ".join(sorted({t.strip() for t in targets_list if t and t.strip()}))

            elif target_source == "azure":
                required_env_vars = ['AZURE_CREDENTIALS']
                missing_vars = [var for var in required_env_vars if os.getenv(var) is None]

                if missing_vars:
                    error_message = f"The following Azure environment variables are missing: {', '.join(missing_vars)}"
                    raise EnvironmentError(error_message)
                else:
                    azure_credentials_json = os.getenv('AZURE_CREDENTIALS', '[]')
                    azure_targets = fetch_azure_ips(azure_credentials_json)
                    targets = " ".join(sorted(set(azure_targets)))

            elif target_source == "aws":  # Add support for AWS as a target source
                required_env_vars = ['AWS_CREDENTIALS']
                missing_vars = [var for var in required_env_vars if os.getenv(var) is None]

                if missing_vars:
                    error_message = f"The following AWS environment variables are missing: {', '.join(missing_vars)}"
                    raise EnvironmentError(error_message)

                else:
                    aws_credentials_json = os.getenv('AWS_CREDENTIALS', '[]')
                    aws_targets = fetch_aws_ips(aws_credentials_json)
                    targets = " ".join(sorted(set(aws_targets)))

            else:
                logger.error("Invalid target source specified: %s", target_source)
                sys.exit(1)

            # Skip scan if no targets
            if not targets:
                logger.warning("No targets resolved; skipping scan cycle")
                set_target_count(0)
            else:
                target_list = targets.split()
                target_count = len(target_list)
                set_target_count(target_count)
                logger.info(f"Discovered {target_count} targets to scan")

                # Configure batch scanning
                batch_size = int(os.getenv('NMAP_BATCH_SIZE', '50'))  # Default 50 hosts per batch
                max_workers = int(os.getenv('NMAP_CONCURRENT_BATCHES', '4'))  # Default 4 concurrent batches
                nmap_ports = os.getenv('NMAP_PORTS')  # e.g. "22,80,443" or "1-1024"
                nmap_args = os.getenv('NMAP_ARGUMENTS', '-Pn -T4 -sV')  # Added -sV for service detection

                # Split targets into batches
                batches = [target_list[i:i + batch_size] for i in range(0, target_count, batch_size)]
                logger.info(f"Split {target_count} targets into {len(batches)} batches (size: {batch_size}, concurrent: {max_workers})")

                scan_start_time = time.time()
                successful_batches = 0
                failed_batches = 0

                # Collect all unique IPs from scan results for GeoIP enrichment
                all_scan_ips = set()
                batch_results = []

                # Create hostname mapping (original target -> resolved IP)
                hostname_map = {target: target for target in target_list}  # Will be updated during scan

                # Scan batches concurrently
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {executor.submit(scan_batch, batch, nm, nmap_ports, nmap_args): (idx, batch)
                              for idx, batch in enumerate(batches)}

                    for future in as_completed(futures):
                        batch_idx, batch = futures[future]
                        try:
                            nm_result, error = future.result()
                            if nm_result:
                                # Store results for later processing with batch info
                                batch_results.append((nm_result, batch))

                                # Build hostname mapping for this batch
                                for target in batch:
                                    for host in nm_result.all_hosts():
                                        # Try to match hostname to IP
                                        hostname = nm_result[host].hostname()
                                        if hostname and hostname == target:
                                            hostname_map[target] = host
                                        elif host == target:
                                            hostname_map[target] = host
                                        elif target not in hostname_map or hostname_map[target] == target:
                                            # If target is a hostname, use it; resolved IP is in 'host'
                                            if not target.replace('.', '').isdigit():
                                                hostname_map[host] = target

                                # Collect IPs for GeoIP enrichment
                                if geoip_enricher:
                                    for host in nm_result.all_hosts():
                                        all_scan_ips.add(host)

                                expose_nmap_scan_stats(nm_result)
                                successful_batches += 1
                                increment_successful_scans()
                                logger.info(f"Batch {batch_idx + 1}/{len(batches)} completed successfully")
                            else:
                                failed_batches += 1
                                increment_failed_scans()
                                logger.error(f"Batch {batch_idx + 1}/{len(batches)} failed: {error}")
                        except Exception as e:
                            failed_batches += 1
                            increment_failed_scans()
                            logger.error(f"Batch {batch_idx + 1}/{len(batches)} encountered error: {str(e)}")

                # Perform GeoIP enrichment if enabled
                geoip_data = None
                if geoip_enricher and all_scan_ips:
                    logger.info(f"Enriching {len(all_scan_ips)} IPs with GeoIP data...")
                    try:
                        # Run async enrichment in sync context
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        geoip_data = loop.run_until_complete(
                            geoip_enricher.enrich_batch(list(all_scan_ips))
                        )
                        loop.close()
                        logger.info(f"GeoIP enrichment completed for {len(geoip_data)} IPs")
                    except Exception as e:
                        logger.error(f"GeoIP enrichment failed: {str(e)}")
                        geoip_data = None

                # Now expose results with GeoIP data and hostname mapping
                for nm_result, batch in batch_results:
                    expose_nmap_scan_results(nm_result, geoip_data, hostname_map)

                scan_duration = time.time() - scan_start_time
                set_scan_duration(scan_duration)
                logger.info(f"Scan completed in {scan_duration:.2f}s - Success: {successful_batches}/{len(batches)} batches")

            scan_frequency = float(os.getenv('SCAN_FREQUENCY', '36000'))
            logger.info("Sleeping for %s seconds", scan_frequency)
            time.sleep(scan_frequency)

    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt. Exiting.")
        sys.exit(0)
    except Exception as e:
        logger.error("An unexpected error occurred: %s", str(e))

if __name__ == '__main__':
    # Pass the desired port as an argument when calling the function
    EXPORTER_PORT = int(os.getenv('EXPORTER_PORT', '9808'))

    # Initialize GeoIP enricher if enabled (for debug endpoint)
    geoip_enabled = os.getenv('GEOIP_ENABLED', 'false').lower() == 'true'
    geoip_enricher = None

    if geoip_enabled:
        geoip_provider = os.getenv('GEOIP_PROVIDER', 'ipapi.co')
        geoip_cache_ttl = int(os.getenv('GEOIP_CACHE_TTL', '86400'))
        geoip_api_token = os.getenv('GEOIP_API_TOKEN')

        geoip_enricher = GeoIPEnricher(
            provider=geoip_provider,
            cache_ttl=geoip_cache_ttl,
            api_token=geoip_api_token
        )

    start_prometheus_server(EXPORTER_PORT, geoip_enricher)
    main()
