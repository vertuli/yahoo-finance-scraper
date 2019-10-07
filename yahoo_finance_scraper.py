import requests
import logging
import json
import re
import pathlib
from bs4.element import Tag
from bs4 import BeautifulSoup
from itertools import chain
from typing import Dict, List, Optional, Union
from datetime import datetime

TICKERS_PATH = pathlib.Path("tickers.txt")
DATA_DIR = pathlib.Path("data")
LOGS_DIR = pathlib.Path("logs")
LOGS_FORMAT = "%(asctime)s|%(levelname)s|%(funcName)s|%(message)s"
DATE_TODAY = datetime.now().strftime('%Y-%m-%d')


def main() -> None:
    create_dirs()
    data_path = DATA_DIR / f"{DATE_TODAY}.json"
    log_path = LOGS_DIR / f"{DATE_TODAY}.log"
    logging.basicConfig(filename=log_path, level=logging.DEBUG, format=LOGS_FORMAT)
    scrape_pages(data_path)


def create_dirs() -> None:
    if not DATA_DIR.exists():
        DATA_DIR.mkdir()
    if not LOGS_DIR.exists():
        LOGS_DIR.mkdir()


def scrape_pages(data_path: pathlib.Path) -> None:
    tickers = get_tickers(data_path)
    for ticker in tickers:
        scraped_page = scrape_page(ticker)
        with data_path.open('a') as f:
            record = json.dumps(scraped_page) + "\n"
            f.write(record)


def get_tickers(data_path: pathlib.Path) -> List[str]:
    if not TICKERS_PATH.exists():
        TICKERS_PATH.touch()
        TICKERS_PATH.write_text("\n".join(["X", "LOL", "GM"]))  # Test tickers.
    with TICKERS_PATH.open() as f:
        tickers = [line.strip() for line in f.readlines()]
    if data_path.exists():
        tickers = remove_scraped_tickers(tickers, data_path)
    logging.info(f"Using {len(tickers)} tickers found in {TICKERS_PATH}.")
    return tickers


def remove_scraped_tickers(tickers: List[str], data_path: pathlib.Path) -> List[str]:
    num_read_tickers = len(tickers)
    with data_path.open() as f:
        for line in f.readlines():
            scraped_ticker = json.loads(line).get('ticker')
            if scraped_ticker:
                tickers.remove(scraped_ticker)
    num_removed = num_read_tickers - len(tickers)
    logging.warning(f"Skipping {num_removed} tickers already scraped at {data_path}!")
    return tickers


def scrape_page(ticker: str) -> Dict[str, str]:
    scraped_page = {"ticker": ticker}
    rows = get_page_rows(ticker)
    if rows:
        scraped_page["date_accessed"] = DATE_TODAY
    for row in rows:
        scraped_row = scrape_row(row)
        if scraped_row:
            scraped_page.update(scraped_row)
    return scraped_page


def get_page_rows(ticker: str) -> List[Tag]:
    url = f"https://finance.yahoo.com/quote/{ticker}/key-statistics?p={ticker}"
    response = requests.get(url)
    if response.url != url:
        logging.warning(f"No page exists for ticker {ticker}!")
        logging.debug(f"No content at requested URL: {url}")
        rows = []
    else:
        logging.debug(f"Page exists for ticker {ticker}.")
        soup = BeautifulSoup(response.content, "lxml")
        logging.debug(f"BeautifulSoup object created from URL: {url}")
        rows = list(chain.from_iterable([table("tr") for table in soup("tbody")]))
        logging.info(f"Found {len(rows)} rows for ticker {ticker}.")
    return rows


def scrape_row(row: Tag) -> Dict[str, str]:
    scraped_row = {}
    raw_tags = get_tags(row)
    vals = [format_tag_val(raw_tag) for raw_tag in raw_tags]
    if vals and vals[0] != "" and vals[1] != "":
        logging.debug(f"Scraped row {vals[0]}: {vals[1]}.")
        scraped_row = {vals[0]: vals[1]}
    return scraped_row


def get_tags(row: Tag) -> List[Tag]:
    for sup in row("sup"):
        sup.decompose()
    raw_tags = row("td")
    if len(raw_tags) != 2:
        raw_tags = []
        logging.warning("Row does not contain only two tags!")
        logging.debug(f"Row HTML: {row.prettify()}")
    return raw_tags


def format_tag_val(tag: Tag) -> Union[str, float]:
    raw_val = tag.get_text().strip()

    pat = r"^(?P<sign>[-+])?(?P<number>[\d,]+\.?\d*)(?P<suffix>k|M|B|%)?$"
    match = re.match(pat, raw_val)
    if match:
        number = float(match["number"].replace(',', ''))
        sign = match["sign"]
        suffix = match["suffix"]
        val = format_number(number, sign, suffix)
        return val

    pat = r"^[A-Z][a-z]{2} \d{1,2}, \d{4}$"
    match = re.match(pat, raw_val.strip())
    if match:
        val = datetime.strptime(match.string, "%b %d, %Y").strftime("%Y-%m-%d")
        return val

    val = format_string(raw_val)
    return val


def format_number(number: float, sign: Optional[str], suffix: Optional[str]) -> float:
    if sign == "-":
        number = number * -1
    if suffix == 'k':
        number = number * 10 ** 3
    if suffix == "M":
        number = number * 10 ** 6
    if suffix == "B":
        number = number * 10 ** 9
    if suffix == "%":
        number = number / 100.0
    return number


def format_string(raw_val: str) -> str:
    val = (
        raw_val.replace("N/A", "")
        .replace("%", "pct")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
        .replace(",", "")
        .replace("S&P", "snp")
        .strip()
        .lower()
        .replace(" ", "_")
    )
    return val


if __name__ == "__main__":
    main()
