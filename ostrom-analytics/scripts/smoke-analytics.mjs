import assert from "node:assert/strict";
import { enrichSeries, heatmap, hourlyAverages, summarize } from "../src/lib/analytics";
import {
  generateDemoConsumption,
  generateDemoSpotPrices,
} from "../src/lib/ostrom/demo";

const end = new Date("2025-06-15T00:00:00.000Z");
const start = new Date("2025-06-01T00:00:00.000Z");

const consumption = generateDemoConsumption(start, end, "HOUR");
const prices = generateDemoSpotPrices(start, end);
const enriched = enrichSeries(consumption, prices);
const stats = summarize(enriched, prices);
const hours = hourlyAverages(enriched);
const heat = heatmap(enriched);

assert.ok(consumption.length > 24 * 10, "enough hourly points");
assert.equal(consumption.length, prices.length);
assert.ok(stats.totalKwh > 50, "demo household uses meaningful energy");
assert.ok(stats.variableCostEur != null && stats.variableCostEur > 0);
assert.ok(stats.fixedCostEur != null && stats.fixedCostEur > 0);
assert.ok(stats.totalCostEur != null && stats.totalCostEur > stats.variableCostEur);
assert.equal(hours.length, 24);
assert.equal(heat.length, 7 * 24);
assert.ok(hours.some((h) => h.avgKwh > 0.3), "evening/morning peak present");

console.log("analytics smoke ok", {
  hours: consumption.length,
  totalKwh: stats.totalKwh,
  variableCostEur: stats.variableCostEur,
  fixedCostEur: stats.fixedCostEur,
  totalCostEur: stats.totalCostEur,
});
