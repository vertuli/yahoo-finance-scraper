# yahoo-finance-scraper

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)

Get daily company statistics scraped from Yahoo! Finance in JSON line format.

* Reads line-delimited list of tickers from `tickers.txt`.
* Data organized by date of scraping to `data/2019-10-06.json`, for example.
* Logs likewise to `logs/2019-10-06.log`. 
* Skips already scraped data for the day in case it needs to be run again.