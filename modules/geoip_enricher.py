#!/usr/bin/env python3

from __future__ import absolute_import
import time
import logging
import asyncio
import aiohttp
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class GeoIPEnricher:
    """
    Enriches IP addresses with GeoIP metadata (ASN, ISP, location, connection type).
    Caches results to avoid redundant API calls and rate limits.
    """
    
    def __init__(self, provider: str = "ipapi.co", cache_ttl: int = 86400, api_token: Optional[str] = None):
        """
        Initialize the GeoIP enricher.
        
        Args:
            provider: GeoIP provider name (currently supports "ipapi.co")
            cache_ttl: Cache time-to-live in seconds (default: 24 hours)
            api_token: Optional API token for the provider
        """
        self.provider = provider
        self.cache_ttl = cache_ttl
        self.api_token = api_token
        self._cache: Dict[str, tuple] = {}  # ip -> (data, timestamp)
        
        logger.info(f"GeoIP enricher initialized (provider={provider}, cache_ttl={cache_ttl}s)")
    
    def _is_cache_valid(self, ip: str) -> bool:
        """Check if cached data for IP is still valid"""
        if ip not in self._cache:
            return False
        
        _, timestamp = self._cache[ip]
        return (time.time() - timestamp) < self.cache_ttl
    
    def _infer_connection_type(self, isp: str, org: str, asn: str) -> str:
        """
        Infer connection type based on ISP/ASN/org name patterns.
        
        Args:
            isp: ISP name
            org: Organization name
            asn: ASN number/name
            
        Returns:
            Connection type: "mobile", "fibre", "dsl", "datacentre", or "unknown"
        """
        # Combine all fields for analysis
        combined = f"{isp} {org} {asn}".lower()
        
        # Mobile/LTE patterns
        mobile_keywords = ["mobile", "lte", "4g", "5g", "cellular", "wireless", "vodafone", "t-mobile", "verizon", "at&t", "att"]
        if any(kw in combined for kw in mobile_keywords):
            return "mobile"
        
        # Data center patterns
        datacenter_keywords = ["aws", "amazon", "azure", "microsoft", "google cloud", "gcp", "hetzner", "ovh", 
                              "digitalocean", "linode", "vultr", "datacentre", "datacenter", "hosting", "cloud"]
        if any(kw in combined for kw in datacenter_keywords):
            return "datacentre"
        
        # Fiber/DSL patterns
        fiber_keywords = ["fiber", "fibre", "ftth", "fttp"]
        if any(kw in combined for kw in fiber_keywords):
            return "fibre"
        
        dsl_keywords = ["dsl", "vdsl", "adsl", "broadband"]
        if any(kw in combined for kw in dsl_keywords):
            return "dsl"
        
        return "unknown"
    
    async def _fetch_ipapi_co(self, session: aiohttp.ClientSession, ip: str) -> Optional[Dict]:
        """
        Fetch GeoIP data from ipapi.co
        
        Args:
            session: aiohttp session
            ip: IP address to lookup
            
        Returns:
            Dictionary with GeoIP data or None on error
        """
        url = f"https://ipapi.co/{ip}/json/"
        headers = {}
        
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        
        try:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "asn": data.get("asn", ""),
                        "org": data.get("org", ""),
                        "isp": data.get("org", ""),  # ipapi.co uses "org" for ISP
                        "country": data.get("country_code", ""),
                        "city": data.get("city", ""),
                        "region": data.get("region", ""),
                        "latitude": data.get("latitude", ""),
                        "longitude": data.get("longitude", ""),
                    }
                elif response.status == 429:
                    logger.warning(f"Rate limit hit for IP {ip}")
                    return None
                else:
                    logger.debug(f"Failed to fetch GeoIP for {ip}: HTTP {response.status}")
                    return None
        except asyncio.TimeoutError:
            logger.debug(f"Timeout fetching GeoIP for {ip}")
            return None
        except Exception as e:
            logger.debug(f"Error fetching GeoIP for {ip}: {str(e)}")
            return None
    
    async def enrich(self, ip: str) -> Dict[str, str]:
        """
        Enrich a single IP address with GeoIP metadata.
        
        Args:
            ip: IP address to enrich
            
        Returns:
            Dictionary with GeoIP metadata
        """
        # Check cache first
        if self._is_cache_valid(ip):
            data, _ = self._cache[ip]
            logger.debug(f"Using cached GeoIP data for {ip}")
            return data
        
        # Fetch from provider
        async with aiohttp.ClientSession() as session:
            if self.provider == "ipapi.co":
                raw_data = await self._fetch_ipapi_co(session, ip)
            else:
                logger.error(f"Unsupported GeoIP provider: {self.provider}")
                raw_data = None
        
        # If fetch failed, return cached data if available, otherwise empty data
        if raw_data is None:
            if ip in self._cache:
                data, _ = self._cache[ip]
                logger.debug(f"Using stale cached GeoIP data for {ip}")
                return data
            else:
                return self._empty_data()
        
        # Infer connection type
        connection_type = self._infer_connection_type(
            raw_data.get("isp", ""),
            raw_data.get("org", ""),
            raw_data.get("asn", "")
        )
        
        # Build enriched data
        enriched_data = {
            "asn": str(raw_data.get("asn", "")),
            "isp": raw_data.get("isp", ""),
            "org": raw_data.get("org", ""),
            "country": raw_data.get("country", ""),
            "city": raw_data.get("city", ""),
            "region": raw_data.get("region", ""),
            "connection_type": connection_type,
        }
        
        # Cache the result
        self._cache[ip] = (enriched_data, time.time())
        logger.debug(f"Cached GeoIP data for {ip}: {enriched_data}")
        
        return enriched_data
    
    async def enrich_batch(self, ips: list) -> Dict[str, Dict[str, str]]:
        """
        Enrich multiple IP addresses in parallel.
        
        Args:
            ips: List of IP addresses to enrich
            
        Returns:
            Dictionary mapping IP -> GeoIP metadata
        """
        tasks = [self.enrich(ip) for ip in ips]
        results = await asyncio.gather(*tasks)
        return {ip: result for ip, result in zip(ips, results)}
    
    def _empty_data(self) -> Dict[str, str]:
        """Return empty GeoIP data structure"""
        return {
            "asn": "",
            "isp": "",
            "org": "",
            "country": "",
            "city": "",
            "region": "",
            "connection_type": "unknown",
        }
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        valid_entries = sum(1 for ip in self._cache if self._is_cache_valid(ip))
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "stale_entries": len(self._cache) - valid_entries,
        }
    
    def get_cached_data(self) -> Dict[str, Dict]:
        """Get all cached GeoIP data (for debug endpoint)"""
        result = {}
        for ip, (data, timestamp) in self._cache.items():
            result[ip] = {
                **data,
                "cached_at": timestamp,
                "is_valid": self._is_cache_valid(ip),
            }
        return result
