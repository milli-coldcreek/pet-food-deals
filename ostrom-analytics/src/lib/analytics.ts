import { format, getDay, getHours, parseISO } from "date-fns";
import { grossPriceCt } from "./ostrom/client";
import type {
  ConsumptionPoint,
  EnrichedPoint,
  SpotPricePoint,
} from "./ostrom/types";

export function enrichSeries(
  consumption: ConsumptionPoint[],
  prices: SpotPricePoint[],
): EnrichedPoint[] {
  const priceMap = new Map<string, number>();
  for (const p of prices) {
    const key = hourKey(p.date);
    priceMap.set(key, grossPriceCt(p));
  }

  return consumption.map((c) => {
    const key = hourKey(c.date);
    const priceCt = priceMap.get(key) ?? null;
    const costEur =
      priceCt == null ? null : Math.round(((c.kWh * priceCt) / 100) * 10000) / 10000;
    return {
      date: c.date,
      timestamp: parseISO(c.date).getTime(),
      kWh: c.kWh,
      priceCt,
      costEur,
    };
  });
}

function hourKey(iso: string): string {
  const d = parseISO(iso);
  return `${d.getUTCFullYear()}-${d.getUTCMonth()}-${d.getUTCDate()}-${d.getUTCHours()}`;
}

export interface SummaryStats {
  totalKwh: number;
  totalCostEur: number | null;
  avgDailyKwh: number;
  peakKwh: number;
  peakAt: string | null;
  avgPriceCt: number | null;
  cheapestHour: { hour: number; avgKwh: number; avgPriceCt: number | null } | null;
  mostExpensiveHour: {
    hour: number;
    avgKwh: number;
    avgPriceCt: number | null;
  } | null;
  hoursCovered: number;
  costCoveragePct: number;
}

export function summarize(points: EnrichedPoint[]): SummaryStats {
  if (points.length === 0) {
    return {
      totalKwh: 0,
      totalCostEur: null,
      avgDailyKwh: 0,
      peakKwh: 0,
      peakAt: null,
      avgPriceCt: null,
      cheapestHour: null,
      mostExpensiveHour: null,
      hoursCovered: 0,
      costCoveragePct: 0,
    };
  }

  let totalKwh = 0;
  let totalCost = 0;
  let costPoints = 0;
  let priceSum = 0;
  let peakKwh = -1;
  let peakAt: string | null = null;

  for (const p of points) {
    totalKwh += p.kWh;
    if (p.costEur != null && p.priceCt != null) {
      totalCost += p.costEur;
      costPoints += 1;
      priceSum += p.priceCt;
    }
    if (p.kWh > peakKwh) {
      peakKwh = p.kWh;
      peakAt = p.date;
    }
  }

  const dayKeys = new Set(
    points.map((p) => format(parseISO(p.date), "yyyy-MM-dd")),
  );
  const avgDailyKwh = totalKwh / Math.max(dayKeys.size, 1);

  const byHour = hourlyAverages(points);
  const withPrice = byHour.filter((h) => h.avgPriceCt != null);
  const cheapestHour =
    withPrice.length > 0
      ? withPrice.reduce((a, b) =>
          (a.avgPriceCt ?? Infinity) <= (b.avgPriceCt ?? Infinity) ? a : b,
        )
      : byHour.length
        ? byHour.reduce((a, b) => (a.avgKwh <= b.avgKwh ? a : b))
        : null;
  const mostExpensiveHour =
    withPrice.length > 0
      ? withPrice.reduce((a, b) =>
          (a.avgPriceCt ?? -Infinity) >= (b.avgPriceCt ?? -Infinity) ? a : b,
        )
      : byHour.length
        ? byHour.reduce((a, b) => (a.avgKwh >= b.avgKwh ? a : b))
        : null;

  return {
    totalKwh: round(totalKwh, 2),
    totalCostEur: costPoints ? round(totalCost, 2) : null,
    avgDailyKwh: round(avgDailyKwh, 2),
    peakKwh: round(peakKwh, 3),
    peakAt,
    avgPriceCt: costPoints ? round(priceSum / costPoints, 2) : null,
    cheapestHour,
    mostExpensiveHour,
    hoursCovered: points.length,
    costCoveragePct: round((costPoints / points.length) * 100, 0),
  };
}

export interface HourBucket {
  hour: number;
  avgKwh: number;
  avgPriceCt: number | null;
  avgCostEur: number | null;
  samples: number;
}

export function hourlyAverages(points: EnrichedPoint[]): HourBucket[] {
  const buckets = Array.from({ length: 24 }, (_, hour) => ({
    hour,
    kWh: 0,
    price: 0,
    priceN: 0,
    cost: 0,
    costN: 0,
    samples: 0,
  }));

  for (const p of points) {
    const hour = getHours(parseISO(p.date));
    const b = buckets[hour];
    b.kWh += p.kWh;
    b.samples += 1;
    if (p.priceCt != null) {
      b.price += p.priceCt;
      b.priceN += 1;
    }
    if (p.costEur != null) {
      b.cost += p.costEur;
      b.costN += 1;
    }
  }

  return buckets.map((b) => ({
    hour: b.hour,
    avgKwh: b.samples ? round(b.kWh / b.samples, 3) : 0,
    avgPriceCt: b.priceN ? round(b.price / b.priceN, 2) : null,
    avgCostEur: b.costN ? round(b.cost / b.costN, 4) : null,
    samples: b.samples,
  }));
}

export interface HeatCell {
  day: number; // 0=Sun
  hour: number;
  avgKwh: number;
  samples: number;
}

export function heatmap(points: EnrichedPoint[]): HeatCell[] {
  const map = new Map<string, { sum: number; n: number }>();
  for (const p of points) {
    const d = parseISO(p.date);
    const key = `${getDay(d)}-${getHours(d)}`;
    const cur = map.get(key) ?? { sum: 0, n: 0 };
    cur.sum += p.kWh;
    cur.n += 1;
    map.set(key, cur);
  }

  const cells: HeatCell[] = [];
  for (let day = 0; day < 7; day++) {
    for (let hour = 0; hour < 24; hour++) {
      const cur = map.get(`${day}-${hour}`);
      cells.push({
        day,
        hour,
        avgKwh: cur ? round(cur.sum / cur.n, 3) : 0,
        samples: cur?.n ?? 0,
      });
    }
  }
  return cells;
}

export interface LoadShiftInsight {
  title: string;
  detail: string;
  potentialSavingEur: number | null;
}

export function loadShiftInsights(points: EnrichedPoint[]): LoadShiftInsight[] {
  const insights: LoadShiftInsight[] = [];
  const priced = points.filter((p) => p.priceCt != null && p.costEur != null);
  if (priced.length < 24) {
    insights.push({
      title: "Connect prices for cost insights",
      detail:
        "With spot prices available, we can estimate how much shifting evening load could save.",
      potentialSavingEur: null,
    });
    return insights;
  }

  const prices = priced.map((p) => p.priceCt as number);
  const avg = prices.reduce((a, b) => a + b, 0) / prices.length;
  const expensive = priced.filter((p) => (p.priceCt as number) > avg * 1.15);
  const cheap = priced.filter((p) => (p.priceCt as number) < avg * 0.85);

  if (expensive.length && cheap.length) {
    const expensiveKwh = expensive.reduce((s, p) => s + p.kWh, 0);
    const avgExp = expensive.reduce((s, p) => s + (p.priceCt as number), 0) / expensive.length;
    const avgCheap = cheap.reduce((s, p) => s + (p.priceCt as number), 0) / cheap.length;
    const shiftable = expensiveKwh * 0.2; // assume 20% of peak-price load is movable
    const saving = (shiftable * (avgExp - avgCheap)) / 100;

    insights.push({
      title: "Shift ~20% of peak-price load",
      detail: `Moving flexible load from expensive hours (avg ${avgExp.toFixed(1)} ct) into cheaper hours (avg ${avgCheap.toFixed(1)} ct) could cut costs.`,
      potentialSavingEur: round(saving, 2),
    });
  }

  const evening = priced.filter((p) => {
    const h = getHours(parseISO(p.date));
    return h >= 17 && h <= 21;
  });
  const midday = priced.filter((p) => {
    const h = getHours(parseISO(p.date));
    return h >= 11 && h <= 15;
  });
  if (evening.length && midday.length) {
    const eAvg =
      evening.reduce((s, p) => s + (p.priceCt as number), 0) / evening.length;
    const mAvg =
      midday.reduce((s, p) => s + (p.priceCt as number), 0) / midday.length;
    insights.push({
      title: "Solar midday vs evening peak",
      detail: `Midday averaged ${mAvg.toFixed(1)} ct/kWh vs evening ${eAvg.toFixed(1)} ct/kWh. Dishwashers, laundry, and EV charging love midday.`,
      potentialSavingEur: null,
    });
  }

  return insights;
}

export function aggregateDaily(points: EnrichedPoint[]): EnrichedPoint[] {
  const map = new Map<string, EnrichedPoint>();
  for (const p of points) {
    const key = format(parseISO(p.date), "yyyy-MM-dd");
    const existing = map.get(key);
    if (!existing) {
      map.set(key, {
        date: `${key}T00:00:00.000Z`,
        timestamp: parseISO(`${key}T00:00:00.000Z`).getTime(),
        kWh: p.kWh,
        priceCt: p.priceCt,
        costEur: p.costEur,
      });
    } else {
      existing.kWh += p.kWh;
      if (p.costEur != null) {
        existing.costEur = (existing.costEur ?? 0) + p.costEur;
      }
      if (p.priceCt != null) {
        existing.priceCt =
          existing.priceCt == null
            ? p.priceCt
            : (existing.priceCt + p.priceCt) / 2;
      }
    }
  }
  return Array.from(map.values())
    .map((p) => ({
      ...p,
      kWh: round(p.kWh, 3),
      priceCt: p.priceCt == null ? null : round(p.priceCt, 2),
      costEur: p.costEur == null ? null : round(p.costEur, 4),
    }))
    .sort((a, b) => a.timestamp - b.timestamp);
}

function round(n: number, digits: number) {
  const f = 10 ** digits;
  return Math.round(n * f) / f;
}
