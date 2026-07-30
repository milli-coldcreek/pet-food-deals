# Wattwise — Ostrom electricity analytics

A small web app for exploring your **Ostrom** smart-meter consumption with charts the official app doesn’t expose: hourly/daily series with spot-price overlay, average day profiles, week×hour heatmaps, and rough load-shift savings estimates.

## Features

- **Demo mode** — realistic synthetic household data so you can poke around immediately
- **Live mode** — connect with Ostrom Developer Portal credentials (`client_id` / `client_secret`)
- Consumption + spot price overlay (gross ct/kWh including taxes & levies)
- Average-hour profile and week×hour heatmap
- Period presets: 7 / 14 / 30 / 90 days
- Credentials stay in `sessionStorage` and are only forwarded to Ostrom through the local API proxy

## Quick start

```bash
cd ostrom-analytics
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### Live Ostrom data

1. Open the [Ostrom Developer Portal](https://developer.ostrom-api.io/) and sign in with your Ostrom app account
2. Create a **Production** API client and copy the client ID + secret
3. In Wattwise, choose **Connect my account**, paste the credentials, and load

Requires a smart meter (IMSYS) for hourly consumption. Spot prices work for dynamic tariffs; ZIP is taken from your contract for taxes/grid fees.

## Scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Local development |
| `npm run build` | Production build |
| `npm run start` | Serve production build |
| `npm run lint` | ESLint |

## Stack

Next.js (App Router) · TypeScript · Recharts · Ostrom REST API (`/contracts`, `/energy-consumption`, `/spot-prices`)

Not affiliated with Ostrom.
