import asyncio
import aiohttp
import yaml
import os
import pandas as pd
from bs4 import BeautifulSoup
import cv2
import numpy as np
from tqdm import tqdm
from urllib.parse import urlparse
import time
from typing import List, Dict
import logging
import json
from playwright.async_api import async_playwright
import yt_dlp
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TikTokProcessor:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Create output directories
        os.makedirs(self.config['output_dir'], exist_ok=True)
        os.makedirs(os.path.join(self.config['output_dir'], self.config['thumbnails_dir']), exist_ok=True)
        
        # Set API credentials from environment variables (with fallback to config file)
        self.config['tiktok_api']['api_key'] = os.getenv('TIKTOK_API_KEY', self.config['tiktok_api'].get('api_key', ''))
        self.config['tiktok_api']['api_secret'] = os.getenv('TIKTOK_API_SECRET', self.config['tiktok_api'].get('api_secret', ''))
        
        # Set default browser wait timeout if not specified in config
        if 'browser_wait_timeout' not in self.config:
            self.config['browser_wait_timeout'] = 10000  # Default 10 seconds
            
        # Set default user agent if not specified in config
        if 'browser_user_agent' not in self.config:
            self.config['browser_user_agent'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
        
        # Log a warning if API credentials are not set and API is enabled
        if self.config['tiktok_api']['use_api'] and not self.config['tiktok_api']['api_key']:
            logger.warning("TikTok API is enabled but API key is not set. Please add TIKTOK_API_KEY to your .env file.")
        
        self.session = None
        self.results = []
        self.browser = None
        self.context = None

    async def init_session(self):
        """Initialize HTTP session and browser context"""
        self.session = aiohttp.ClientSession()
        
        # Initialize headless browser if not using API
        if not self.config['tiktok_api']['use_api']:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
            self.context = await self.browser.new_context(
                user_agent=self.config['browser_user_agent'],
                viewport={'width': 1920, 'height': 1080}
            )

    async def close_session(self):
        """Close all sessions and browser"""
        if self.session:
            await self.session.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    def get_video_id(self, url: str) -> str:
        """Extract video ID from TikTok URL"""
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        return path.split('/')[-1]

    async def _get_video_metadata_api(self, video_id: str) -> Dict:
        """Get video metadata using TikTok API"""
        headers = {
            "Authorization": f"Bearer {self.config['tiktok_api']['api_key']}",
            "Content-Type": "application/json"
        }
        
        data = {
            "video_ids": [video_id],
            "fields": [
                "id",
                "title",
                "video_description",
                "duration",
                "height",
                "width",
                "cover_image_url",
                "share_url",
                "create_time",
                "author",
                "statistics"
            ]
        }
        
        async with self.session.post(
            self.config['tiktok_api']['api_endpoint'],
            headers=headers,
            json=data
        ) as response:
            if response.status != 200:
                raise Exception(f"API request failed: {response.status}")
            return await response.json()

    async def _get_video_metadata_browser(self, url: str) -> Dict:
        """Get video metadata using headless browser"""
        page = await self.context.new_page()
        try:
            # Add extra headers and cookies to appear more like a real browser
            await page.set_extra_http_headers({
                'Accept-Language': 'en-US,en;q=0.9',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Sec-Ch-Ua': '"Chromium";v="118", "Google Chrome";v="118"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1'
            })
            
            logger.info(f"Navigating to {url}")
            await page.goto(url, wait_until="networkidle", timeout=self.config['browser_wait_timeout'])
            
            # Wait for the video data to load
            logger.info("Waiting for video description to appear")
            await page.wait_for_selector('[data-e2e="video-desc"]', timeout=self.config['browser_wait_timeout'])
            
            # Wait a bit more to ensure everything is loaded
            await asyncio.sleep(2)
            
            # Extract metadata from the page
            logger.info("Extracting metadata")
            metadata = {
                'author': await page.evaluate('() => document.querySelector("[data-e2e=\"user-username\"]")?.textContent?.trim()'),
                'likes': await page.evaluate('() => document.querySelector("[data-e2e=\"like-count\"]")?.textContent?.trim()'),
                'comments': await page.evaluate('() => document.querySelector("[data-e2e=\"comment-count\"]")?.textContent?.trim()'),
                'views': await page.evaluate('() => document.querySelector("[data-e2e=\"view-count\"]")?.textContent?.trim()'),
                'description': await page.evaluate('() => document.querySelector("[data-e2e=\"video-desc\"]")?.textContent?.trim()'),
                'video_url': await page.evaluate('() => document.querySelector("video")?.src')
            }
            
            logger.info(f"Metadata extracted: {metadata}")
            return metadata
        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}")
            # Take a screenshot for debugging
            screenshot_path = os.path.join(self.config['output_dir'], f"error_{self.get_video_id(url)}.png")
            await page.screenshot(path=screenshot_path)
            logger.info(f"Error screenshot saved to {screenshot_path}")
            raise
        finally:
            await page.close()

    async def _download_video(self, url: str, video_id: str) -> str:
        """Download video using yt-dlp"""
        ydl_opts = {
            'format': 'best',
            'outtmpl': os.path.join(self.config['output_dir'], f'{video_id}.%(ext)s'),
            'quiet': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    async def _generate_thumbnail(self, video_path: str, video_id: str):
        """Generate thumbnail from video file"""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception("Could not open video file")
        
        # Get the middle frame
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        middle_frame = total_frames // 2
        cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame)
        
        ret, frame = cap.read()
        if not ret:
            raise Exception("Could not read video frame")
        
        # Resize frame to desired thumbnail size
        frame = cv2.resize(frame, tuple(self.config['thumbnail_size']))
        
        # Save thumbnail
        thumbnail_path = os.path.join(self.config['output_dir'], self.config['thumbnails_dir'], f"{video_id}.jpg")
        cv2.imwrite(thumbnail_path, frame)
        
        cap.release()
        return thumbnail_path

    async def process_url(self, url: str) -> Dict:
        """Process a single TikTok URL"""
        try:
            logger.info(f"Processing URL: {url}")
            video_id = self.get_video_id(url)
            
            # Get metadata
            if self.config['tiktok_api']['use_api']:
                metadata = await self._get_video_metadata_api(video_id)
            else:
                metadata = await self._get_video_metadata_browser(url)
            
            # Download video
            logger.info(f"Downloading video: {video_id}")
            video_path = await self._download_video(url, video_id)
            
            # Generate thumbnail
            logger.info(f"Generating thumbnail for: {video_id}")
            thumbnail_path = await self._generate_thumbnail(video_path, video_id)
            
            # Clean up video file
            os.remove(video_path)
            
            # Prepare result
            result = {
                'url': url,
                'video_id': video_id,
                'author': metadata.get('author', 'Unknown'),
                'likes': metadata.get('likes', 0),
                'comments': metadata.get('comments', 0),
                'views': metadata.get('views', 0),
                'description': metadata.get('description', ''),
                'thumbnail_path': thumbnail_path
            }
            
            logger.info(f"Successfully processed: {video_id}")
            return result

        except Exception as e:
            logger.error(f"Error processing {url}: {str(e)}")
            return None

    async def process_batch(self, urls: List[str]):
        """Process a batch of URLs concurrently"""
        tasks = [self.process_url(url) for url in urls]
        results = await asyncio.gather(*tasks)
        self.results.extend([r for r in results if r is not None])

    async def process_all_urls(self, urls: List[str]):
        """Process all URLs in batches"""
        await self.init_session()
        
        batch_size = self.config['concurrent_requests']
        for i in tqdm(range(0, len(urls), batch_size)):
            batch = urls[i:i + batch_size]
            await self.process_batch(batch)
            
            if i + batch_size < len(urls):
                await asyncio.sleep(self.config['batch_wait_time'])

        await self.close_session()

    def save_results(self):
        """Save results to CSV file"""
        if not self.results:
            logger.warning("No results to save")
            return

        df = pd.DataFrame(self.results)
        output_path = os.path.join(self.config['output_dir'], 'tiktok_data.csv')
        df.to_csv(output_path, index=False)
        logger.info(f"Results saved to {output_path}")

async def main():
    # Example usage
    urls = [
        "https://www.tiktok.com/@user1/video/1234567890",
        "https://www.tiktok.com/@user2/video/0987654321",
        # Add more URLs here
    ]

    processor = TikTokProcessor()
    await processor.process_all_urls(urls)
    processor.save_results()

if __name__ == "__main__":
    asyncio.run(main()) 