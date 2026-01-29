import os
import requests
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def trigger_backup():
    # Use internal URL if running in the same Railway project, 
    # or the public URL/localhost for local testing
    base_url = os.environ.get("BACKEND_URL", "http://localhost:8000")
    endpoint = f"{base_url.rstrip('/')}/api/v1/pwa/backup/trigger"
    
    cron_secret = os.environ.get("CRON_SECRET")
    
    if not cron_secret:
        logger.error("CRON_SECRET environment variable is not set")
        sys.exit(1)
        
    logger.info(f"Triggering backup at {endpoint}...")
    
    try:
        response = requests.post(
            endpoint,
            headers={"X-Cron-Secret": cron_secret},
            timeout=300  # Backups might take a while
        )
        
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Backup successful! URL: {data.get('backup_url')}")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to trigger backup: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response content: {e.response.text}")
        sys.exit(1)

if __name__ == "__main__":
    trigger_backup()
