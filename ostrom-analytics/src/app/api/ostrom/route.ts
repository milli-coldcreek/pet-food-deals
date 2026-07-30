import { NextResponse } from "next/server";
import {
  getAccessToken,
  getContracts,
  getEnergyConsumption,
  getSpotPrices,
} from "@/lib/ostrom/client";
import {
  DEMO_CONTRACT,
  generateDemoConsumption,
  generateDemoSpotPrices,
} from "@/lib/ostrom/demo";
import type { Environment, Resolution } from "@/lib/ostrom/types";

export interface ProxyBody {
  mode: "live" | "demo";
  clientId?: string;
  clientSecret?: string;
  environment?: Environment;
  action: "contracts" | "consumption" | "prices" | "bundle";
  contractId?: number;
  zip?: string;
  startDate?: string;
  endDate?: string;
  resolution?: Resolution;
}

async function liveToken(body: ProxyBody) {
  if (!body.clientId || !body.clientSecret) {
    throw new Error("clientId and clientSecret are required for live mode");
  }
  const env = body.environment ?? "production";
  const token = await getAccessToken(body.clientId, body.clientSecret, env);
  return { token: token.access_token, env };
}

export async function POST(req: Request) {
  try {
    const body = (await req.json()) as ProxyBody;

    if (body.mode === "demo") {
      return NextResponse.json(handleDemo(body));
    }

    const { token, env } = await liveToken(body);

    if (body.action === "contracts") {
      const contracts = await getContracts(token, env);
      return NextResponse.json({ contracts });
    }

    if (body.action === "consumption") {
      if (!body.contractId || !body.startDate || !body.endDate || !body.resolution) {
        return NextResponse.json(
          { error: "contractId, startDate, endDate, resolution required" },
          { status: 400 },
        );
      }
      const consumption = await getEnergyConsumption(
        token,
        env,
        body.contractId,
        body.startDate,
        body.endDate,
        body.resolution,
      );
      return NextResponse.json({ consumption });
    }

    if (body.action === "prices") {
      if (!body.startDate || !body.endDate) {
        return NextResponse.json(
          { error: "startDate and endDate required" },
          { status: 400 },
        );
      }
      const prices = await getSpotPrices(
        token,
        env,
        body.startDate,
        body.endDate,
        body.zip,
      );
      return NextResponse.json({ prices });
    }

    if (body.action === "bundle") {
      if (!body.contractId || !body.startDate || !body.endDate) {
        return NextResponse.json(
          { error: "contractId, startDate, endDate required" },
          { status: 400 },
        );
      }
      const resolution = body.resolution ?? "HOUR";
      const [contracts, consumption, prices] = await Promise.all([
        getContracts(token, env),
        getEnergyConsumption(
          token,
          env,
          body.contractId,
          body.startDate,
          body.endDate,
          resolution,
        ),
        getSpotPrices(token, env, body.startDate, body.endDate, body.zip),
      ]);
      return NextResponse.json({ contracts, consumption, prices });
    }

    return NextResponse.json({ error: "Unknown action" }, { status: 400 });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Request failed";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

function handleDemo(body: ProxyBody) {
  const end = body.endDate ? new Date(body.endDate) : new Date();
  const start = body.startDate
    ? new Date(body.startDate)
    : new Date(end.getTime() - 14 * 24 * 60 * 60 * 1000);
  const resolution = body.resolution ?? "HOUR";

  if (body.action === "contracts") {
    return { contracts: [DEMO_CONTRACT] };
  }

  if (body.action === "consumption") {
    return {
      consumption: generateDemoConsumption(start, end, resolution),
    };
  }

  if (body.action === "prices") {
    return {
      prices: generateDemoSpotPrices(start, end, body.zip ?? DEMO_CONTRACT.address.zip),
    };
  }

  return {
    contracts: [DEMO_CONTRACT],
    consumption: generateDemoConsumption(start, end, resolution),
    prices: generateDemoSpotPrices(start, end, DEMO_CONTRACT.address.zip),
  };
}
