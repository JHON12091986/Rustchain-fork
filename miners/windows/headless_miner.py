#!/usr/bin/env python3
"""
RustChain Windows Headless Miner
Runs in background without GUI, with automatic retry and diagnostics.
"""

import sys
import time
import requests
import json
import os
from pathlib import Path

# Maximum retry attempts to prevent infinite loops
MAX_RETRY_ATTEMPTS = 3

# Configuration
NODE_URL = os.environ.get("RUSTCHAIN_NODE_URL", "https://rustchain.org")
WALLET_ID = os.environ.get("RUSTCHAIN_WALLET", "JHON12091986")
HEADER_INTERVAL = int(os.environ.get("RUSTCHAIN_HEADER_INTERVAL", "60"))  # seconds

def log(msg, level="INFO"):
    """Print log message with timestamp to stderr."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}", file=sys.stderr)

def submit_header():
    """Submit a header to the RustChain node."""
    url = f"{NODE_URL}/api/header/submit"
    payload = {
        "miner_id": WALLET_ID,
        "timestamp": int(time.time()),
        "version": "2.2.1"
    }
    
    retry_count = 0
    while retry_count < MAX_RETRY_ATTEMPTS:
        try:
            log(f"Submitting header (attempt {retry_count + 1}/{MAX_RETRY_ATTEMPTS})")
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 429:
                retry_count += 1
                sleep_time = 2 ** retry_count
                log(f"Rate limited (429). Retry {retry_count}/{MAX_RETRY_ATTEMPTS} after {sleep_time}s", "WARN")
                time.sleep(sleep_time)
                continue
                
            if response.status_code == 403:
                log(f"Server rejected header: {response.text}", "ERROR")
                return False
                
            if response.status_code != 200:
                retry_count += 1
                log(f"HTTP {response.status_code}. Retry {retry_count}/{MAX_RETRY_ATTEMPTS}", "WARN")
                time.sleep(2 ** retry_count)
                continue
                
            data = response.json()
            if data.get("ok"):
                log(f"Header accepted. Nonce: {data.get('nonce', 'unknown')}")
                return True
            else:
                log(f"Header rejected: {data.get('error', 'unknown error')}", "ERROR")
                return False
                
        except requests.exceptions.Timeout:
            retry_count += 1
            log(f"Timeout. Retry {retry_count}/{MAX_RETRY_ATTEMPTS}", "WARN")
            time.sleep(2 ** retry_count)
            
        except requests.exceptions.ConnectionError as e:
            retry_count += 1
            log(f"Connection error: {e}. Retry {retry_count}/{MAX_RETRY_ATTEMPTS}", "WARN")
            time.sleep(2 ** retry_count)
            
        except Exception as e:
            retry_count += 1
            log(f"Unexpected error: {e}. Retry {retry_count}/{MAX_RETRY_ATTEMPTS}", "ERROR")
            time.sleep(2 ** retry_count)
    
    log("ERROR: Max retry attempts reached. Exiting.", "ERROR")
    return False

def main():
    """Main entry point for headless miner."""
    log("Starting RustChain Windows Headless Miner")
    log(f"Node URL: {NODE_URL}")
    log(f"Wallet ID: {WALLET_ID}")
    log(f"Header interval: {HEADER_INTERVAL}s")
    log(f"Max retry attempts: {MAX_RETRY_ATTEMPTS}")
    
    consecutive_failures = 0
    max_consecutive_failures = 5
    
    while True:
        try:
            success = submit_header()
            
            if success:
                consecutive_failures = 0
                log("Header submitted successfully. Sleeping...")
                time.sleep(HEADER_INTERVAL)
            else:
                consecutive_failures += 1
                log(f"Submission failed. Consecutive failures: {consecutive_failures}", "ERROR")
                
                if consecutive_failures >= max_consecutive_failures:
                    log(f"ERROR: {max_consecutive_failures} consecutive failures. Exiting.", "ERROR")
                    sys.exit(1)
                    
                # Exponential backoff after failures
                sleep_time = 2 ** consecutive_failures
                log(f"Sleeping {sleep_time}s before retry...", "WARN")
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            log("Received interrupt signal. Exiting gracefully.")
            sys.exit(0)
            
        except Exception as e:
            log(f"Unexpected error in main loop: {e}", "ERROR")
            time.sleep(30)

if __name__ == "__main__":
    main()