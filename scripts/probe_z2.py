import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bs4 import BeautifulSoup
from src.scrapers.base import http_get
URL = "https://www.zooplus.de/shop/katzen/katzenfutter_dose/royal_canin_katzenfutter/royal_canin_mature/113466?activeVariant=113466.10"
soup = BeautifulSoup(http_get(URL).text, "html.parser")
data = json.loads(soup.find("script", id="__NEXT_DATA__").string)
text = json.dumps(data)
import re
# find numbers like 1529, 1376, 15.29, 13.76 near price/discount/rabatt
for m in re.finditer(r'"(?:[^"]*(?:price|Price|rabatt|Rabatt|discount|Discount)[^"]*)"\s*:\s*([0-9.]+)', text):
    v = float(m.group(1))
    if v > 100 and v < 10000:
        print('cents?', m.group(0)[:80], v, 'eur', v/100)
    elif 5 < v < 50:
        print('eur?', m.group(0)[:80], v)
