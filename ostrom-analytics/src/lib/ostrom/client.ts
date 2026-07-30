import type {
  ConsumptionPoint,
  Contract,
  Environment,
  Resolution,
  SpotPricePoint,
} from "./types";

function apiBase(env: Environment) {
  return env === "sandbox"
    ? "https://sandbox.ostrom-api.io"
    : "https://production.ostrom-api.io";
}

function authBase(env: Environment) {
  return env === "sandbox"
    ? "https://auth.sandbox.ostrom-api.io"
    : "https://auth.production.ostrom-api.io";
}

export async function getAccessToken(
  clientId: string,
  clientSecret: string,
  environment: Environment,
): Promise<{ access_token: string; expires_in: number }> {
  const basic = Buffer.from(`${clientId}:${clientSecret}`).toString("base64");
  const res = await fetch(`${authBase(environment)}/oauth2/token`, {
    method: "POST",
    headers: {
      Authorization: `Basic ${basic}`,
      "Content-Type": "application/x-www-form-urlencoded",
      Accept: "application/json",
    },
    body: "grant_type=client_credentials",
    cache: "no-store",
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Auth failed (${res.status}): ${text}`);
  }

  return res.json();
}

async function authenticatedGet<T>(
  path: string,
  token: string,
  environment: Environment,
  params?: Record<string, string>,
): Promise<T> {
  const url = new URL(`${apiBase(environment)}${path}`);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      url.searchParams.set(k, v);
    }
  }

  const res = await fetch(url.toString(), {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/json",
    },
    cache: "no-store",
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Ostrom API ${path} failed (${res.status}): ${text}`);
  }

  return res.json();
}

export async function getContracts(
  token: string,
  environment: Environment,
): Promise<Contract[]> {
  const data = await authenticatedGet<{ data: Contract[] }>(
    "/contracts",
    token,
    environment,
  );
  return data.data ?? [];
}

export async function getEnergyConsumption(
  token: string,
  environment: Environment,
  contractId: number | string,
  startDate: string,
  endDate: string,
  resolution: Resolution,
): Promise<ConsumptionPoint[]> {
  const data = await authenticatedGet<{ data: ConsumptionPoint[] }>(
    `/contracts/${contractId}/energy-consumption`,
    token,
    environment,
    { startDate, endDate, resolution },
  );
  return data.data ?? [];
}

export async function getSpotPrices(
  token: string,
  environment: Environment,
  startDate: string,
  endDate: string,
  zip?: string,
): Promise<SpotPricePoint[]> {
  const params: Record<string, string> = {
    startDate,
    endDate,
    resolution: "HOUR",
  };
  if (zip) params.zip = zip;

  const data = await authenticatedGet<{ data: SpotPricePoint[] }>(
    "/spot-prices",
    token,
    environment,
    params,
  );
  return data.data ?? [];
}

/**
 * Variable energy price in ct/kWh (incl. VAT), per Ostrom docs:
 * https://docs.ostrom-api.io/docs/fetching-prices
 * total variable = (grossKwhPrice + grossKwhTaxAndLevies) * kWh
 */
export function grossPriceCt(p: SpotPricePoint): number {
  return p.grossKwhPrice + p.grossKwhTaxAndLevies;
}

/**
 * Monthly fixed costs in EUR (incl. VAT), per Ostrom docs:
 * grossMonthlyOstromBaseFee + grossMonthlyGridFees
 */
export function monthlyFixedFeesEur(p: SpotPricePoint): number {
  return p.grossMonthlyOstromBaseFee + p.grossMonthlyGridFees;
}
