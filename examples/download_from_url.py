#!/usr/bin/env python3
"""
Example: Download memory image from URL and start analysis.

This demonstrates using the URL download feature which is ideal for:
- Large files (10GB+) that are slow to upload via browser
- Remote storage (S3, GCS, HTTP endpoints)
- Automated pipelines where files are already on a server
- Non-blocking downloads (server fetches in background)
"""

import time
import requests
from typing import Optional


class ForensicsClient:
    """Client for Volatility 3 Memory Forensics Platform."""
    
    def __init__(self, base_url: str, token: str):
        """Initialize client."""
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def download_from_url(
        self,
        url: str,
        description: Optional[str] = None
    ) -> dict:
        """
        Queue download of memory image from URL.
        
        Args:
            url: Direct download URL (http:// or https://)
            description: Optional description for the image
        
        Returns:
            Response dict with image_id and status
        
        Example:
            result = client.download_from_url(
                url='https://storage.example.com/dumps/memory.raw',
                description='Production server - 2025-12-24'
            )
            print(f"Image ID: {result['image_id']}")
        """
        response = requests.post(
            f'{self.base_url}/api/v1/upload/from-url',
            headers=self.headers,
            json={
                'url': url,
                'description': description or f'Downloaded from {url}'
            }
        )
        
        if response.status_code not in (201, 202):
            raise Exception(f"Download failed: {response.text}")
        
        return response.json()
    
    def check_download_status(self, image_id: str) -> dict:
        """
        Check download progress/status.
        
        Args:
            image_id: UUID of the image being downloaded
        
        Returns:
            Status dict with progress information
        """
        response = requests.get(
            f'{self.base_url}/api/v1/upload/status/{image_id}',
            headers=self.headers
        )
        
        if response.status_code == 404:
            return {'status': 'not_found', 'image_id': image_id}
        
        if response.status_code != 200:
            raise Exception(f"Status check failed: {response.text}")
        
        return response.json()
    
    def create_job(
        self,
        image_id: str,
        plugins: list,
        priority: int = 5
    ) -> dict:
        """
        Create analysis job for memory image.
        
        Args:
            image_id: UUID of uploaded/downloaded image
            plugins: List of Volatility plugins to run
            priority: Job priority (1-10, higher = more urgent)
        
        Returns:
            Job dict with job_id and status
        """
        response = requests.post(
            f'{self.base_url}/api/v1/jobs/',
            headers=self.headers,
            json={
                'memory_image_id': image_id,
                'plugins': plugins,
                'priority': priority
            }
        )
        
        if response.status_code != 201:
            raise Exception(f"Job creation failed: {response.text}")
        
        return response.json()
    
    def get_job_status(self, job_id: str) -> dict:
        """Get current job status."""
        response = requests.get(
            f'{self.base_url}/api/v1/jobs/{job_id}',
            headers=self.headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get job status: {response.text}")
        
        return response.json()


def example_download_large_file():
    """Example 1: Download large file from remote URL."""
    client = ForensicsClient(
        base_url='http://localhost:8000',
        token='YOUR_JWT_TOKEN_HERE'
    )
    
    print("=== Example 1: Download from URL ===\n")
    
    # Queue async download (returns immediately)
    result = client.download_from_url(
        url='https://example.com/dumps/server-memory-2025-12-24.raw',
        description='Production Linux server memory dump'
    )
    
    image_id = result['image_id']
    print(f"✅ Download queued!")
    print(f"   Image ID: {image_id}")
    print(f"   Status: {result.get('message', 'Queued')}\n")
    
    # Poll status until download completes
    print("Checking download progress...")
    for attempt in range(60):  # 60 attempts = 5 minutes max
        status = client.check_download_status(image_id)
        
        if status['status'] == 'completed':
            print(f"   ✅ Download complete!")
            print(f"      File size: {status['file_size_bytes'] / (1024**3):.2f} GB")
            print(f"      SHA256: {status['file_hash_sha256']}\n")
            return image_id
        
        elif status['status'] == 'downloading':
            if 'percent_complete' in status:
                print(f"   ⏳ {status['percent_complete']}% complete", end='\r')
        
        elif status['status'] == 'error':
            print(f"   ❌ Download failed: {status.get('error')}")
            return None
        
        time.sleep(5)  # Check every 5 seconds
    
    print("\n⚠️  Download timeout (5 minutes)")
    return None


def example_download_and_analyze():
    """Example 2: Download file and immediately start analysis."""
    client = ForensicsClient(
        base_url='http://localhost:8000',
        token='YOUR_JWT_TOKEN_HERE'
    )
    
    print("=== Example 2: Download and Analyze ===\n")
    
    # Queue download
    print("Queuing download...")
    result = client.download_from_url(
        url='https://storage.example.com/dumps/memory.raw',
        description='Web server memory - incident investigation'
    )
    image_id = result['image_id']
    print(f"✅ Queued. Image ID: {image_id}\n")
    
    # Wait for download to complete
    print("Waiting for download to complete...")
    status = None
    for attempt in range(60):
        status = client.check_download_status(image_id)
        if status['status'] == 'completed':
            print(f"✅ Download complete! ({status['file_size_bytes'] / (1024**3):.2f} GB)\n")
            break
        time.sleep(5)
    
    if status and status['status'] != 'completed':
        print("❌ Download failed or timeout")
        return
    
    # Start analysis
    print("Starting analysis...")
    job = client.create_job(
        image_id=image_id,
        plugins=['pslist', 'pstree', 'netscan', 'cmdline', 'malfind', 'filescan'],
        priority=8
    )
    job_id = job['id']
    print(f"✅ Analysis started. Job ID: {job_id}\n")
    
    # Monitor job progress
    print("Monitoring progress...")
    while True:
        job_status = client.get_job_status(job_id)
        total = job_status['total_plugins']
        completed = job_status['completed_plugins']
        
        if job_status['status'] == 'completed':
            print(f"\n✅ Analysis complete!")
            print(f"   Plugins executed: {completed}/{total}")
            print(f"   Artifacts extracted: {job_status.get('artifacts_extracted', 0)}")
            break
        
        else:
            progress = (completed / total * 100) if total > 0 else 0
            print(f"   {job_status['status']}: {completed}/{total} plugins ({progress:.0f}%)", end='\r')
        
        time.sleep(10)


def example_batch_download():
    """Example 3: Download multiple files for batch analysis."""
    client = ForensicsClient(
        base_url='http://localhost:8000',
        token='YOUR_JWT_TOKEN_HERE'
    )
    
    print("=== Example 3: Batch Download ===\n")
    
    urls = [
        'https://storage.example.com/server1-memory.raw',
        'https://storage.example.com/server2-memory.raw',
        'https://storage.example.com/server3-memory.raw',
    ]
    
    image_ids = []
    
    # Queue all downloads
    print("Queuing downloads...")
    for url in urls:
        result = client.download_from_url(url=url)
        image_ids.append(result['image_id'])
        print(f"   ✅ {url.split('/')[-1]} (ID: {result['image_id']})")
    
    print(f"\nQueued {len(image_ids)} downloads\n")
    
    # Monitor all downloads in parallel
    print("Monitoring downloads...")
    completed_ids = set()
    
    while len(completed_ids) < len(image_ids):
        for image_id in image_ids:
            if image_id in completed_ids:
                continue
            
            status = client.check_download_status(image_id)
            if status['status'] == 'completed':
                print(f"✅ Download complete: {image_id}")
                completed_ids.add(image_id)
        
        if len(completed_ids) < len(image_ids):
            time.sleep(10)
    
    print(f"\n✅ All {len(image_ids)} downloads completed!")
    return image_ids


if __name__ == '__main__':
    # Set your actual API token
    TOKEN = 'your_jwt_token_here'
    
    print("\n" + "=" * 60)
    print("Volatility 3 Memory Forensics Platform - URL Download Examples")
    print("=" * 60 + "\n")
    
    print("IMPORTANT: Update TOKEN variable with your actual JWT token!\n")
    
    print("Available examples:")
    print("1. example_download_large_file() - Download and wait for completion")
    print("2. example_download_and_analyze() - Download then start analysis")
    print("3. example_batch_download() - Download multiple files in parallel\n")
    
    print("To run an example, uncomment the function call below and run this script.\n")
    
    # Uncomment to run:
    # example_download_large_file()
    # example_download_and_analyze()
    # example_batch_download()
