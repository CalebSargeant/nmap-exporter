#!/usr/bin/env python3

"""
Manual demonstration of GeoIP enrichment feature.
Shows how the enricher works with example data.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from modules.geoip_enricher import GeoIPEnricher


def demonstrate_connection_type_inference():
    """Demonstrate connection type inference with example ISPs"""
    enricher = GeoIPEnricher(provider="ipapi.co", cache_ttl=3600)
    
    print("=" * 70)
    print("GeoIP Enrichment Feature - Connection Type Inference Demo")
    print("=" * 70)
    print()
    
    test_cases = [
        ("Amazon AWS", "Amazon.com Inc.", "AS16509", "Google's 8.8.8.8"),
        ("Vodafone Mobile", "Vodafone", "AS12345", "Mobile network"),
        ("Fiber Networks", "FiberCo", "AS55555", "Fiber ISP"),
        ("DSL Provider", "DSL Co", "AS88888", "DSL connection"),
        ("Generic ISP", "ISP Limited", "AS11111", "Unknown type"),
    ]
    
    print("Connection Type Inference Examples:")
    print("-" * 70)
    
    for isp, org, asn, description in test_cases:
        conn_type = enricher._infer_connection_type(isp, org, asn)
        print(f"\n{description}")
        print(f"  ISP: {isp}")
        print(f"  Org: {org}")
        print(f"  ASN: {asn}")
        print(f"  → Inferred Type: {conn_type}")
    
    print("\n" + "=" * 70)
    print("Cache Statistics:")
    print("-" * 70)
    stats = enricher.get_cache_stats()
    print(f"  Total entries: {stats['total_entries']}")
    print(f"  Valid entries: {stats['valid_entries']}")
    print(f"  Stale entries: {stats['stale_entries']}")
    
    print("\n" + "=" * 70)
    print("Metric Example:")
    print("-" * 70)
    print("""
When enabled, metrics are enriched with GeoIP labels:

nmap_scan_results_geoip{
    host="8.8.8.8",
    protocol="tcp",
    name="http",
    product_detected="",
    isp="Google LLC",
    asn="AS15169",
    country="US",
    city="Mountain View",
    connection_type="datacentre"
} 80
    """)
    
    print("=" * 70)
    print("\nTo enable GeoIP enrichment, set these environment variables:")
    print("-" * 70)
    print("  GEOIP_ENABLED=true")
    print("  GEOIP_PROVIDER=ipapi.co")
    print("  GEOIP_CACHE_TTL=86400")
    print("  GEOIP_API_TOKEN=<optional>")
    print()
    print("Access cached data at: http://localhost:9808/debug/geoip")
    print("=" * 70)


if __name__ == '__main__':
    demonstrate_connection_type_inference()
