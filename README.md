# TikTok Data Extractor

This project processes TikTok URLs to extract metadata and generate thumbnails for videos. It can process multiple URLs concurrently and saves the results to a CSV file.

## Features

- Concurrent processing of multiple TikTok URLs
- Extracts metadata including:
  - Author information
  - Like count
  - Comment count
  - View count
- Generates thumbnails for each video
- Configurable batch processing with wait times
- Saves results to CSV with thumbnail paths

## Installation

1. Clone this repository
2. Install the required dependencies:
```bash
pip install -r requirements.txt
```
3. If using Playwright (for browser-based extraction), install browsers:
```bash
playwright install chromium
```

## Configuration

### Environment Variables
Create a `.env` file in the root directory based on the provided `env.example` file:
```bash
cp env.example .env
```

Edit the `.env` file to add your TikTok API credentials:
```
TIKTOK_API_KEY=your_api_key_here
TIKTOK_API_SECRET=your_api_secret_here
```

### YAML Configuration
Copy the example configuration file:
```bash
cp config.yaml.example config.yaml
```

Edit the `config.yaml` file to adjust the following parameters:
- `concurrent_requests`: Number of concurrent requests to make
- `batch_wait_time`: Time to wait between batches in seconds
- `output_dir`: Directory to store thumbnails and output files
- `thumbnails_dir`: Subdirectory for thumbnails
- `thumbnail_size`: Width and height of generated thumbnails
- `tiktok_api.use_api`: Set to `true` to use the TikTok API, or `false` to use browser-based extraction

## Extraction Methods

### TikTok API Method (Recommended)
- Set `tiktok_api.use_api` to `true` in config.yaml
- Requires TikTok API credentials in the `.env` file
- More reliable and respects TikTok's terms of service

### Browser-based Method
- Set `tiktok_api.use_api` to `false` in config.yaml
- Uses Playwright to automate a browser session
- May be affected by TikTok's anti-scraping measures
- Does not require API credentials

## Usage

1. Edit the `tiktok_processor.py` file to add your list of TikTok URLs in the `main()` function
2. Run the script:
```bash
python tiktok_processor.py
```

The script will:
1. Process all URLs in batches
2. Generate thumbnails for each video
3. Extract metadata
4. Save results to a CSV file in the output directory

## Output

The script generates:
1. A CSV file (`tiktok_data.csv`) containing all extracted metadata
2. Thumbnail images in the specified thumbnails directory

## Notes

- Make sure to respect TikTok's terms of service and rate limits when using this tool. 