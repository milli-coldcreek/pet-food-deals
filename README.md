# Pet Food Deal Tracker

Free price monitor for **Fressnapf**, **Zooplus**, and **Zooroyal**. Give a **product name** and **pack size** — the tracker searches all three shops and sends **Telegram** alerts when the price hits your target. No URLs to maintain.

## Quick start

### 1. Add your products

Edit [`products.yaml`](products.yaml):

```yaml
products:
  - name: "Royal Canin Instinctive in Soße"
    pet: "Cats"
    search_query: "Royal Canin Instinctive in Soße"
    pack_size: "12x85g"
    target_price: 15.00
    retailers:
      - fressnapf
      - zooplus
      - zooroyal
```

| Field | Purpose |
|-------|---------|
| `search_query` | What to search for on each shop |
| `pack_size` | Pack you care about (e.g. `12x85g`) — used for matching and per-piece math |
| `target_price` | Target **total** price for that pack (e.g. €15 for 12×85 g → €1.25/pouch) |
| `retailers` | Which shops to check (defaults to all three) |

### 2. Set up Telegram (free, ~2 minutes)

1. Message **@BotFather** → `/newbot` → copy the **bot token**
2. Message your new bot once
3. Get your **chat ID** from `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. For GitHub Actions, add secrets `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`

### 3. Run locally

```powershell
cd C:\Users\Milena\Projects\pet-food-deals
pip install -r requirements.txt
$env:TELEGRAM_BOT_TOKEN = "your-token"
$env:TELEGRAM_CHAT_ID = "your-chat-id"
python -m src.main
```

**First run** records baseline prices per shop (no alerts). **Later runs** alert when:

- Price is at or below `target_price` (or **€/piece** is at or below your implied per-piece target)
- Price drops `min_discount_pct` below baseline (optional, default 10%)
- A retailer sale brings price below baseline
- A **different multipack** (e.g. 48×85 g) or **seasonal variant** is cheap per piece while your usual listing is not

Each shop is checked independently — you get an alert for whichever hits your target first.

### 4. Schedule with GitHub Actions (free)

Push to GitHub, add Telegram secrets, and the workflow runs twice daily. See [`.github/workflows/check-prices.yml`](.github/workflows/check-prices.yml).

## How matching works

For each retailer the tracker:

1. Searches using your `search_query`
2. Scores results by name similarity and `pack_size` match (Sparpakets are preferred — they're often the best price)
3. Compares **€/piece** so a 48-pack can alert as cheap even when the total is above your 12-pack target
4. Skips wrong variants for the **primary** listing (+7 vs adult, Gelee vs Soße, etc.)
5. **Also scans** seasonal editions and other multipack sizes (e.g. 48×85 g when you watch 12×85 g)
6. Stores matched URLs in `state.json` — re-searches every run so broken links don't matter

## Cost

€0 — plain HTTP search/scraping, Telegram Bot API, GitHub Actions free tier.

## Troubleshooting

- **MISS — no matching product** — try a shorter `search_query` or check the product exists on that shop
- **Wrong variant matched** — make `search_query` more specific (e.g. include "in Soße" not just "Instinctive")
- **No alert yet** — current prices may be above your `target_price`; first run only sets baselines
