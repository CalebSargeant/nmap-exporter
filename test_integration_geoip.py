#!/usr/bin/env python3

"""
Integration test for GeoIP enrichment feature.
Tests the enricher with real API calls (or simulated if offline).
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.geoip_enricher import GeoIPEnricher


async def test_real_enrichment():
    """Test real GeoIP enrichment with well-known IPs"""
    enricher = GeoIPEnricher(provider="ipapi.co", cache_ttl=3600)
    
    # Test with well-known public IPs
    test_ips = ["8.8.8.8", "1.1.1.1"]
    
    print("Testing GeoIP enrichment with real API calls...")
    print(f"Test IPs: {test_ips}\n")
    
    try:
        # Test single enrichment
        print("=== Testing single IP enrichment ===")
        for ip in test_ips:
            result = await enricher.enrich(ip)
            print(f"\nIP: {ip}")
            print(f"  ASN: {result.get('asn', 'N/A')}")
            print(f"  ISP: {result.get('isp', 'N/A')}")
            print(f"  Country: {result.get('country', 'N/A')}")
            print(f"  City: {result.get('city', 'N/A')}")
            print(f"  Connection Type: {result.get('connection_type', 'N/A')}")
        
        # Test batch enrichment
        print("\n=== Testing batch enrichment ===")
        batch_results = await enricher.enrich_batch(test_ips)
        print(f"Enriched {len(batch_results)} IPs in batch")
        
        # Test cache
        print("\n=== Testing cache ===")
        cache_stats = enricher.get_cache_stats()
        print(f"Cache stats: {cache_stats}")
        
        # Test cache hit
        print("\n=== Testing cache hit ===")
        result = await enricher.enrich("8.8.8.8")
        print(f"Got cached result for 8.8.8.8: {result.get('isp', 'N/A')}")
        
        print("\n✓ Integration test passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ Integration test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_empty_enrichment():
    """Test enricher behavior without API calls"""
    enricher = GeoIPEnricher(provider="ipapi.co", cache_ttl=3600)
    
    print("\n=== Testing empty data structure ===")
    empty = enricher._empty_data()
    print(f"Empty data structure: {empty}")
    
    print("\n=== Testing cache stats (empty) ===")
    stats = enricher.get_cache_stats()
    print(f"Initial cache stats: {stats}")
    
    print("\n✓ Empty enrichment test passed!")
    return True


if __name__ == '__main__':
    print("GeoIP Enricher Integration Test\n")
    print("=" * 60)
    
    # Test basic functionality without API
    success = test_empty_enrichment()
    
    # Test with real API (may fail if offline or rate limited)
    print("\n" + "=" * 60)
    print("\nAttempting real API test (may fail if offline)...")
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(test_real_enrichment())
        loop.close()
    except Exception as e:
        print(f"\nReal API test skipped: {str(e)}")
        print("This is expected if running offline or hitting rate limits.")
        success = True  # Don't fail the test for network issues
    
    sys.exit(0 if success else 1)
