# TikTok Extractor

A tool to extract data and thumbnails from TikTok videos.

## Features

- Extract metadata from TikTok videos
- Download thumbnails
- Save data to CSV file
- Support for batch processing

## Setup

1. Clone the repository:
```bash
git clone https://github.com/zivisaiah/tiktok_extractor.git
cd tiktok_extractor
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install browser for Playwright:
```bash
python -m playwright install chromium
```

5. Create configuration files:
```bash
cp .env.example .env
# Edit .env with your actual API credentials if using the API method
```

## Usage

1. Create a file named `tiktok_urls.txt` with one TikTok URL per line:
```
https://www.tiktok.com/@username/video/12345678
https://www.tiktok.com/@username/video/87654321
```

2. Run the processor:
```bash
python run_tiktok_processor.py
```

3. Check the `output` directory for results:
- `output/tiktok_data.csv`: CSV file with metadata
- `output/thumbnails/`: Directory with video thumbnails

## Configuration

Modify `config.yaml` to change settings:

- `concurrent_requests`: Number of URLs to process concurrently
- `batch_wait_time`: Time to wait between batches
- `output_dir`: Directory for output files
- `thumbnails_dir`: Subdirectory for thumbnails
- `thumbnail_size`: Width and height of thumbnails
- `tiktok_api.use_api`: Set to true to use TikTok API, false for browser-based scraping

## Notes

- Make sure to respect TikTok's terms of service and rate limits when using this tool. 