#!/usr/bin/env python3

from __future__ import absolute_import
import time
import sys
import os
import json
import nmap
import logging
from modules.ip_fetcher import fetch_azure_ips, fetch_ips_from_file, fetch_aws_ips
from modules.prometheus_format import expose_nmap_scan_results, expose_nmap_scan_stats, start_prometheus_server

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Main function
def main():
    try:
        # Print logo
        with open('ascii_logo.txt', 'r') as file:
            # Read and print the content
            content = file.read()
            print(content)

        nm = nmap.PortScanner()

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
            else:
                logger.info("Scanning targets: %s", targets)
                try:
                    nmap_ports = os.getenv('NMAP_PORTS')  # e.g. "22,80,443" or "1-1024"
                    nmap_args = os.getenv('NMAP_ARGUMENTS', '-Pn -T4')
                    nm.scan(hosts=targets, ports=nmap_ports if nmap_ports else None, arguments=nmap_args)
                    expose_nmap_scan_results(nm)
                    expose_nmap_scan_stats(nm)
                    logger.info("Scan completed successfully")
                except nmap.PortScannerError as e:
                    logger.error("Nmap scan failed: %s", str(e))
                except Exception as e:
                    logger.error("Unexpected error during scan: %s", str(e))

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
    start_prometheus_server(EXPORTER_PORT)
    main()
