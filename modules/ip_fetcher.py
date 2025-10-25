#!/usr/bin/env python3

from __future__ import absolute_import
import os
import json
import boto3
from azure.identity import ClientSecretCredential
from azure.mgmt.subscription import SubscriptionClient
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Function to fetch public IP addresses from file
def fetch_ips_from_file(file_path):
    try:
        with open(file_path, 'r') as f:
            targets = f.read().strip().split("\n")
        return targets
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return []
    except Exception as e:
        logger.error(f"Error reading targets from file: {str(e)}")
        return []

# Function to fetch public IP addresses from Azure
def fetch_azure_ips(credentials_list):
    credentials_list_json = json.loads(credentials_list)
    all_ip_addresses = []

    for credentials in credentials_list_json:
        client_id = credentials.get("AZURE_CLIENT_ID")
        client_secret = credentials.get("AZURE_CLIENT_SECRET")
        tenant_id = credentials.get("AZURE_TENANT_ID")

        try:
            # Azure API URL for fetching public IP addresses
            azure_api_url = "https://management.azure.com/subscriptions/{subscription_id}/providers/Microsoft.Network/publicIPAddresses?api-version=2021-02-01"

            # Azure Management scope for AAD tokens
            scope = "https://management.azure.com/.default"

            # Create a ClientSecretCredential for authentication
            credential = ClientSecretCredential(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)

            # Create a SubscriptionClient to list all accessible subscriptions
            subscription_client = SubscriptionClient(credential)

            # Fetch a list of all subscriptions
            subscriptions = list(subscription_client.subscriptions.list())

            # Extract subscription IDs from the list
            subscription_ids = [subscription.subscription_id for subscription in subscriptions]

            # Get an access token
            token = credential.get_token(scope).token

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            for subscription_id in subscription_ids:
                url = azure_api_url.format(subscription_id=subscription_id)
                while url:
                    response = requests.get(url, headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        for ip_resource in data.get("value", []):
                            ip_address = ip_resource.get("properties", {}).get("ipAddress")
                            if ip_address:
                                all_ip_addresses.append(ip_address)
                        # Handle pagination
                        url = data.get("nextLink")
                    else:
                        logger.error(f"Failed to fetch Azure public IP addresses. Status code: {response.status_code}")
                        return []
        except Exception as e:
            logger.error(f"Error fetching Azure public IP addresses: {str(e)}")
            return []

    return all_ip_addresses


def fetch_aws_ips(credentials_list):
    all_ip_addresses = []

    credentials_list_json = json.loads(credentials_list)
    for credentials in credentials_list_json:
        aws_access_key_id = credentials.get("AWS_ACCESS_KEY_ID")
        aws_secret_access_key = credentials.get("AWS_SECRET_ACCESS_KEY")
        aws_profile_name = credentials.get("AWS_PROFILE_NAME")
        aws_regions = credentials.get("AWS_REGIONS") or []

        for region in aws_regions:
            # Use the specified profile and region to configure AWS credentials
            session = boto3.Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region,
            )

            try:
                # Create an EC2 client using the session
                ec2_client = session.client("ec2")

                # 1) Elastic IPs
                try:
                    response = ec2_client.describe_addresses()
                    for entry in response.get("Addresses", []):
                        public_ip = entry.get("PublicIp")
                        if public_ip:
                            all_ip_addresses.append(public_ip)
                except Exception as e:
                    logger.error(f"describe_addresses failed in region {region}: {str(e)}")

                # 2) Instance public IPs
                try:
                    paginator = ec2_client.get_paginator('describe_instances')
                    for page in paginator.paginate():
                        for reservation in page.get('Reservations', []):
                            for instance in reservation.get('Instances', []):
                                public_ip = instance.get('PublicIpAddress')
                                if public_ip:
                                    all_ip_addresses.append(public_ip)
                except Exception as e:
                    logger.error(f"describe_instances failed in region {region}: {str(e)}")

            except Exception as e:
                # Handle exceptions and log errors
                logger.error(f"Error fetching AWS public IP addresses for profile {aws_profile_name} in region {region}: {str(e)}")
                return []

    # Dedupe
    return list(sorted(set(all_ip_addresses)))
