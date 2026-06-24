import base64
from pathlib import Path
dq = chr(34)
lines = []
lines.append('import json, re, sys\n')
lines.append('from pathlib import Path\n')
lines.append('sys.path.insert(0, str(Path(__file__).resolve().parent.parent))\n')
lines.append('from bs4 import BeautifulSoup\n')
lines.append('from src.scrapers.base import http_get, parse_german_price\n')
lines.append('from src.scrapers.zooplus import ZooplusScraper\n')
lines.append('from src.search.zooplus import ZooplusSearch\n\n')
lines.append('URL = ' + dq + 'https://www.zooplus.de/shop/katzen/katzenfutter_dose/royal_canin_katzenfutter/royal_canin_adult/113463?activeVariant=113463.15' + dq + '\n\n')
lines.append('soup = BeautifulSoup(http_get(URL).text, ' + dq + 'html.parser' + dq + ')\n')
lines.append('data = json.loads(soup.find(' + dq + 'script' + dq + ', id=' + dq + '__NEXT_DATA__' + dq + ').string)\n')
lines.append('text = json.dumps(data)\n')
lines.append(base64.b64decode('Zm9yIG0gaW4gcmUuZmluZGl0ZXIociciKGRpc2NvdW50ZWRQcmljZVJhd3xtaW5BcnRpY2xlUHJpY2VSYXd8cHJpY2VSYXd8Y3VycmVudFByaWNlKSJccyo6XHMqKFswLTkuXSspJywgdGV4dCk6Cg==').decode())
lines.append('    v = float(m.group(2))\n')
lines.append('    if 8 <= v <= 20:\n')
lines.append('        print(m.group(1), v)\n\n')
lines.append('print(' + dq + 'scrape:' + dq + ', ZooplusScraper().scrape(URL).price)\n')
lines.append('print(' + dq + 'search:' + dq + ', ZooplusSearch().search(' + dq + 'Royal Canin Instinctive in So\u00dfe' + dq + ', ' + dq + '12x85g' + dq + '))\n')
Path(r'C:/Users/Milena/Projects/pet-food-deals/scripts/probe_rc_instinctive.py').write_text(''.join(lines), encoding='utf-8')

