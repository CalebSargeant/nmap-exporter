#!/usr/bin/env python3

"""
Unit tests for GeoIP enrichment module, specifically connection type inference.
"""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.geoip_enricher import GeoIPEnricher


class TestConnectionTypeInference(unittest.TestCase):
    """Test connection type inference logic"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.enricher = GeoIPEnricher(provider="ipapi.co", cache_ttl=3600)
    
    def test_mobile_detection(self):
        """Test mobile network detection"""
        # Test various mobile patterns
        test_cases = [
            ("Vodafone Mobile", "Vodafone", "AS12345", "mobile"),
            ("T-Mobile USA", "T-Mobile", "AS21928", "mobile"),
            ("Verizon Wireless", "Verizon", "AS701", "mobile"),
            ("AT&T Mobility", "AT&T", "AS7018", "mobile"),
            ("LTE Network", "Mobile Corp", "AS99999", "mobile"),
            ("5G Services", "Telco", "AS11111", "mobile"),
        ]
        
        for isp, org, asn, expected in test_cases:
            with self.subTest(isp=isp):
                result = self.enricher._infer_connection_type(isp, org, asn)
                self.assertEqual(result, expected, 
                               f"Failed for ISP={isp}, org={org}, asn={asn}")
    
    def test_datacentre_detection(self):
        """Test data center detection"""
        test_cases = [
            ("Amazon AWS", "Amazon.com Inc.", "AS16509", "datacentre"),
            ("Google Cloud", "Google LLC", "AS15169", "datacentre"),
            ("Microsoft Azure", "Microsoft Corporation", "AS8075", "datacentre"),
            ("Hetzner Online", "Hetzner", "AS24940", "datacentre"),
            ("OVH SAS", "OVH", "AS16276", "datacentre"),
            ("DigitalOcean LLC", "DigitalOcean", "AS14061", "datacentre"),
            ("Linode", "Linode LLC", "AS63949", "datacentre"),
        ]
        
        for isp, org, asn, expected in test_cases:
            with self.subTest(isp=isp):
                result = self.enricher._infer_connection_type(isp, org, asn)
                self.assertEqual(result, expected,
                               f"Failed for ISP={isp}, org={org}, asn={asn}")
    
    def test_fibre_detection(self):
        """Test fiber network detection"""
        test_cases = [
            ("Fiber Networks", "FiberCo", "AS55555", "fibre"),
            ("FTTH Services", "HomeFiber", "AS66666", "fibre"),
            ("Fibre Broadband", "ISP Ltd", "AS77777", "fibre"),
        ]
        
        for isp, org, asn, expected in test_cases:
            with self.subTest(isp=isp):
                result = self.enricher._infer_connection_type(isp, org, asn)
                self.assertEqual(result, expected,
                               f"Failed for ISP={isp}, org={org}, asn={asn}")
    
    def test_dsl_detection(self):
        """Test DSL network detection"""
        test_cases = [
            ("DSL Provider", "DSL Co", "AS88888", "dsl"),
            ("VDSL Services", "Telecom", "AS99999", "dsl"),
            ("ADSL Broadband", "ISP Corp", "AS12121", "dsl"),
        ]
        
        for isp, org, asn, expected in test_cases:
            with self.subTest(isp=isp):
                result = self.enricher._infer_connection_type(isp, org, asn)
                self.assertEqual(result, expected,
                               f"Failed for ISP={isp}, org={org}, asn={asn}")
    
    def test_unknown_detection(self):
        """Test unknown connection type for unrecognized patterns"""
        test_cases = [
            ("Generic ISP", "ISP Limited", "AS11111", "unknown"),
            ("Local Network", "Local Co", "AS22222", "unknown"),
        ]
        
        for isp, org, asn, expected in test_cases:
            with self.subTest(isp=isp):
                result = self.enricher._infer_connection_type(isp, org, asn)
                self.assertEqual(result, expected,
                               f"Failed for ISP={isp}, org={org}, asn={asn}")
    
    def test_case_insensitive_detection(self):
        """Test that detection is case-insensitive"""
        result1 = self.enricher._infer_connection_type("AWS", "AMAZON", "AS16509")
        result2 = self.enricher._infer_connection_type("aws", "amazon", "as16509")
        result3 = self.enricher._infer_connection_type("AwS", "AmAzOn", "aS16509")
        
        self.assertEqual(result1, "datacentre")
        self.assertEqual(result2, "datacentre")
        self.assertEqual(result3, "datacentre")
        self.assertEqual(result1, result2)
        self.assertEqual(result2, result3)
    
    def test_priority_mobile_over_datacenter(self):
        """Test that mobile keywords take priority"""
        # If a provider mentions both mobile and cloud, mobile should win
        result = self.enricher._infer_connection_type(
            "Mobile Cloud Services", "Vodafone", "AS12345"
        )
        self.assertEqual(result, "mobile")
    
    def test_priority_datacenter_over_fiber(self):
        """Test that datacenter keywords take priority over fiber"""
        result = self.enricher._infer_connection_type(
            "AWS Fiber Network", "Amazon", "AS16509"
        )
        self.assertEqual(result, "datacentre")


class TestGeoIPEnricherBasics(unittest.TestCase):
    """Test basic GeoIP enricher functionality"""
    
    def test_initialization(self):
        """Test enricher initialization"""
        enricher = GeoIPEnricher(provider="ipapi.co", cache_ttl=7200)
        self.assertEqual(enricher.provider, "ipapi.co")
        self.assertEqual(enricher.cache_ttl, 7200)
        self.assertIsNone(enricher.api_token)
    
    def test_initialization_with_token(self):
        """Test enricher initialization with API token"""
        enricher = GeoIPEnricher(
            provider="ipapi.co", 
            cache_ttl=3600, 
            api_token="test_token"
        )
        self.assertEqual(enricher.api_token, "test_token")
    
    def test_empty_data_structure(self):
        """Test empty data structure"""
        enricher = GeoIPEnricher(provider="ipapi.co", cache_ttl=3600)
        empty_data = enricher._empty_data()
        
        self.assertIn("asn", empty_data)
        self.assertIn("isp", empty_data)
        self.assertIn("country", empty_data)
        self.assertIn("city", empty_data)
        self.assertIn("connection_type", empty_data)
        self.assertEqual(empty_data["connection_type"], "unknown")
    
    def test_cache_stats_empty(self):
        """Test cache stats when empty"""
        enricher = GeoIPEnricher(provider="ipapi.co", cache_ttl=3600)
        stats = enricher.get_cache_stats()
        
        self.assertEqual(stats["total_entries"], 0)
        self.assertEqual(stats["valid_entries"], 0)
        self.assertEqual(stats["stale_entries"], 0)


if __name__ == '__main__':
    unittest.main()
