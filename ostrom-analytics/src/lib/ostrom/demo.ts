import {
  addDays,
  addHours,
  addMonths,
  startOfDay,
  startOfHour,
  startOfMonth,
} from "date-fns";
import type {
  ConsumptionPoint,
  Contract,
  Resolution,
  SpotPricePoint,
} from "./types";

/** Seeded PRNG for stable demo data across reloads. */
function mulberry32(seed: number) {
  return () => {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export const DEMO_CONTRACT: Contract = {
  id: 100523456,
  type: "ELECTRICITY",
  productCode: "SIMPLY_DYNAMIC",
  status: "ACTIVE",
  customerFirstName: "Demo",
  customerLastName: "Customer",
  startDate: "2024-03-22",
  currentMonthlyDepositAmount: 95,
  address: {
    zip: "10115",
    city: "Berlin",
    street: "Invalidenstr.",
    houseNumber: "12",
  },
};

function hourProfile(hour: number, weekday: number): number {
  // Typical German apartment load shape (kWh/h base)
  const weekend = weekday === 0 || weekday === 6;
  const night = hour >= 0 && hour < 6 ? 0.12 : 0;
  const morning = hour >= 6 && hour < 9 ? (weekend ? 0.55 : 0.75) : 0;
  const midday = hour >= 11 && hour < 14 ? (weekend ? 0.65 : 0.35) : 0;
  const evening = hour >= 17 && hour < 22 ? (weekend ? 0.9 : 1.05) : 0;
  const late = hour >= 22 ? 0.35 : 0;
  const base = 0.18;
  return base + night + morning + midday + evening + late;
}

function spotShape(hour: number, dayOffset: number): number {
  // Rough EPEX-like shape: cheap midday/night, expensive evening
  const solarDip = hour >= 11 && hour <= 15 ? -4 : 0;
  const eveningPeak = hour >= 17 && hour <= 20 ? 8 : 0;
  const nightCheap = hour >= 1 && hour <= 5 ? -3 : 0;
  const weekendDip = 0; // applied by caller
  return 8 + solarDip + eveningPeak + nightCheap + weekendDip + dayOffset * 0.15;
}

export function generateDemoConsumption(
  startDate: Date,
  endDate: Date,
  resolution: Resolution,
): ConsumptionPoint[] {
  const rand = mulberry32(42);
  const points: ConsumptionPoint[] = [];

  if (resolution === "HOUR") {
    let cursor = startOfHour(startDate);
    const end = startOfHour(endDate);
    while (cursor < end) {
      const h = cursor.getHours();
      const d = cursor.getDay();
      const noise = (rand() - 0.5) * 0.25;
      const kWh = Math.max(0.05, hourProfile(h, d) + noise);
      points.push({ date: cursor.toISOString(), kWh: Math.round(kWh * 1000) / 1000 });
      cursor = addHours(cursor, 1);
    }
  } else if (resolution === "DAY") {
    let cursor = startOfDay(startDate);
    const end = startOfDay(endDate);
    while (cursor < end) {
      let daySum = 0;
      for (let h = 0; h < 24; h++) {
        daySum += hourProfile(h, cursor.getDay()) + (rand() - 0.5) * 0.2;
      }
      points.push({
        date: cursor.toISOString(),
        kWh: Math.round(daySum * 100) / 100,
      });
      cursor = addDays(cursor, 1);
    }
  } else {
    let cursor = startOfMonth(startDate);
    const end = startOfMonth(endDate);
    while (cursor < end) {
      const days = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 0).getDate();
      let monthSum = 0;
      for (let d = 0; d < days; d++) {
        const day = addDays(cursor, d);
        for (let h = 0; h < 24; h++) {
          monthSum += hourProfile(h, day.getDay()) + (rand() - 0.5) * 0.15;
        }
      }
      points.push({
        date: cursor.toISOString(),
        kWh: Math.round(monthSum * 10) / 10,
      });
      cursor = addMonths(cursor, 1);
    }
  }

  return points;
}

export function generateDemoSpotPrices(
  startDate: Date,
  endDate: Date,
  zip = "10115",
): SpotPricePoint[] {
  void zip;
  const rand = mulberry32(99);
  const points: SpotPricePoint[] = [];
  let cursor = startOfHour(startDate);
  const end = startOfHour(endDate);
  let dayIndex = 0;
  let lastDay = cursor.getDate();

  while (cursor < end) {
    if (cursor.getDate() !== lastDay) {
      dayIndex += 1;
      lastDay = cursor.getDate();
    }
    const weekend = cursor.getDay() === 0 || cursor.getDay() === 6;
    const net = Math.max(
      -2,
      spotShape(cursor.getHours(), dayIndex) +
        (weekend ? -1.5 : 0) +
        (rand() - 0.5) * 3,
    );
    const grossSpot = net * 1.19;
    const netLevies = 16.2;
    const grossLevies = 19.28;

    points.push({
      date: cursor.toISOString(),
      netMwhPrice: net * 10,
      netKwhPrice: Math.round(net * 100) / 100,
      grossKwhPrice: Math.round(grossSpot * 100) / 100,
      netKwhTaxAndLevies: netLevies,
      grossKwhTaxAndLevies: grossLevies,
      netMonthlyOstromBaseFee: 5.04,
      grossMonthlyOstromBaseFee: 6,
      netMonthlyGridFees: 3.84,
      grossMonthlyGridFees: 4.57,
    });
    cursor = addHours(cursor, 1);
  }

  return points;
}
