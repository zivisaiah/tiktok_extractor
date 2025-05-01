import asyncio
from tiktok_processor import TikTokProcessor

async def main():
    # Read URLs from file
    try:
        with open('tiktok_urls.txt', 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
        
        if not urls:
            print("No URLs found in tiktok_urls.txt")
            return
        
        print(f"Found {len(urls)} URLs to process")
        
        # Initialize processor and process URLs
        processor = TikTokProcessor()
        await processor.process_all_urls(urls)
        processor.save_results()
        
        print("Processing complete. Check the output directory for results.")
    
    except FileNotFoundError:
        print("Error: tiktok_urls.txt not found")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 