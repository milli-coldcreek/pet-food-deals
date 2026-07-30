# Wattwise — Ostrom electricity analytics

A small web app for exploring your **Ostrom** smart-meter consumption with charts the official app doesn’t expose: hourly/daily series with spot-price overlay, average day profiles, week×hour heatmaps, and rough load-shift savings estimates.

Built against the official [Ostrom API docs](https://docs.ostrom-api.io/docs/getting-started).

## Features

- **Demo mode** — realistic synthetic household data so you can poke around immediately
- **Live mode** — connect with Ostrom Developer Portal credentials (`client_id` / `client_secret`)
- Consumption + spot price overlay using the documented customer price formula
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

1. Read [Getting Started](https://docs.ostrom-api.io/docs/getting-started) and [Fetching own data](https://docs.ostrom-api.io/docs/ostrom-customer-fetching-own-data)
2. Open the [Ostrom Developer Portal](https://developer.ostrom-api.io/) and sign in with your Ostrom app account
3. Create a **Production** API client and copy the client ID + secret
4. In Wattwise, choose **Connect my account**, paste the credentials, and load

Requires a smart meter (IMSYS) for hourly consumption. Spot prices need a ZIP (taken from your contract) so taxes/grid fees are non-zero — see [Fetching Prices](https://docs.ostrom-api.io/docs/fetching-prices). Day-ahead prices land around **15:00–17:00 CET**.

### Cost formula (from Ostrom docs)

| Part | Calculation |
|------|-------------|
| Variable | `(grossKwhPrice + grossKwhTaxAndLevies) × kWh` (ct → €) |
| Fixed (monthly) | `grossMonthlyOstromBaseFee + grossMonthlyGridFees` |
| Window estimate | variable + fixed prorated by days in the selected range ÷ 30 |

Auth uses OAuth2 client credentials with Basic auth against `auth.production.ostrom-api.io` / `auth.sandbox.ostrom-api.io` ([Authentication](https://docs.ostrom-api.io/reference/authentication)).

OpenAPI: [ostrom-open-api-2023-11-01.json](https://production.ostrom-api.io/ostrom-open-api-2023-11-01.json)

## Scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Local development |
| `npm run build` | Production build |
| `npm run start` | Serve production build |
| `npm run lint` | Typecheck |
| `npm run smoke` | Demo analytics sanity check |

## Stack

Next.js (App Router) · TypeScript · Recharts · Ostrom REST API (`/contracts`, `/energy-consumption`, `/spot-prices`)

Not affiliated with Ostrom.
