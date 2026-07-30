"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { format, parseISO, subDays } from "date-fns";
import {
  aggregateDaily,
  enrichSeries,
  heatmap,
  hourlyAverages,
  loadShiftInsights,
  summarize,
} from "@/lib/analytics";
import type {
  ConsumptionPoint,
  Contract,
  Environment,
  SpotPricePoint,
} from "@/lib/ostrom/types";
import { ConnectScreen } from "@/components/ConnectScreen";
import { OverviewStrip } from "@/components/OverviewStrip";
import { ConsumptionChart } from "@/components/ConsumptionChart";
import { HourlyProfile } from "@/components/HourlyProfile";
import { HeatmapChart } from "@/components/HeatmapChart";
import { InsightsPanel } from "@/components/InsightsPanel";
import { RangeControls } from "@/components/RangeControls";
import styles from "./page.module.css";

const STORAGE_KEY = "ostrom-analytics-session";

export interface Session {
  mode: "live" | "demo";
  clientId?: string;
  clientSecret?: string;
  environment: Environment;
  contractId?: number;
  zip?: string;
}

type RangePreset = "7d" | "14d" | "30d" | "90d";

export default function Home() {
  const [session, setSession] = useState<Session | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [consumption, setConsumption] = useState<ConsumptionPoint[]>([]);
  const [prices, setPrices] = useState<SpotPricePoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preset, setPreset] = useState<RangePreset>("14d");
  const [view, setView] = useState<"hour" | "day">("hour");

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (raw) setSession(JSON.parse(raw) as Session);
    } catch {
      /* ignore */
    }
    setHydrated(true);
  }, []);

  const persist = useCallback((s: Session | null) => {
    setSession(s);
    if (s) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(s));
    else sessionStorage.removeItem(STORAGE_KEY);
  }, []);

  const range = useMemo(() => {
    const end = new Date();
    const days = preset === "7d" ? 7 : preset === "14d" ? 14 : preset === "30d" ? 30 : 90;
    return { start: subDays(end, days), end };
  }, [preset]);

  const fetchBundle = useCallback(
    async (s: Session) => {
      setLoading(true);
      setError(null);
      try {
        const startDate = range.start.toISOString();
        const endDate = range.end.toISOString();

        if (s.mode === "demo") {
          const res = await fetch("/api/ostrom", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              mode: "demo",
              action: "bundle",
              startDate,
              endDate,
              resolution: "HOUR",
            }),
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.error || "Failed to load demo data");
          setContracts(data.contracts);
          setConsumption(data.consumption);
          setPrices(data.prices);
          return;
        }

        let contractId = s.contractId;
        let zip = s.zip;

        if (!contractId) {
          const cRes = await fetch("/api/ostrom", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              mode: "live",
              action: "contracts",
              clientId: s.clientId,
              clientSecret: s.clientSecret,
              environment: s.environment,
            }),
          });
          const cData = await cRes.json();
          if (!cRes.ok) throw new Error(cData.error || "Failed to load contracts");
          setContracts(cData.contracts);
          const active =
            (cData.contracts as Contract[]).find(
              (c) => c.type === "ELECTRICITY" && c.status === "ACTIVE",
            ) ?? cData.contracts[0];
          if (!active) throw new Error("No electricity contract found on this account");
          contractId = active.id;
          zip = active.address?.zip;
          persist({ ...s, contractId, zip });
        }

        const res = await fetch("/api/ostrom", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            mode: "live",
            action: "bundle",
            clientId: s.clientId,
            clientSecret: s.clientSecret,
            environment: s.environment,
            contractId,
            zip,
            startDate,
            endDate,
            resolution: "HOUR",
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Failed to load Ostrom data");
        setContracts(data.contracts);
        setConsumption(data.consumption);
        setPrices(data.prices);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Something went wrong");
      } finally {
        setLoading(false);
      }
    },
    [persist, range.end, range.start],
  );

  useEffect(() => {
    if (session) void fetchBundle(session);
  }, [session, fetchBundle]);

  const enriched = useMemo(
    () => enrichSeries(consumption, prices),
    [consumption, prices],
  );
  const series = useMemo(
    () => (view === "day" ? aggregateDaily(enriched) : enriched),
    [enriched, view],
  );
  const stats = useMemo(() => summarize(enriched), [enriched]);
  const hours = useMemo(() => hourlyAverages(enriched), [enriched]);
  const heat = useMemo(() => heatmap(enriched), [enriched]);
  const insights = useMemo(() => loadShiftInsights(enriched), [enriched]);

  const contract =
    contracts.find((c) => c.id === session?.contractId) ?? contracts[0] ?? null;

  if (!hydrated) {
    return <div className={styles.boot} />;
  }

  if (!session) {
    return (
      <ConnectScreen
        onDemo={() =>
          persist({
            mode: "demo",
            environment: "production",
            contractId: 100523456,
            zip: "10115",
          })
        }
        onConnect={(creds) =>
          persist({
            mode: "live",
            clientId: creds.clientId,
            clientSecret: creds.clientSecret,
            environment: creds.environment,
          })
        }
      />
    );
  }

  return (
    <div className={styles.shell}>
      <header className={styles.topbar}>
        <div className={styles.brandBlock}>
          <span className={styles.mark} aria-hidden />
          <div>
            <p className={styles.brand}>Wattwise</p>
            <p className={styles.sub}>
              {session.mode === "demo"
                ? "Demo household · Berlin"
                : contract
                  ? `${contract.address.city} · ${contract.productCode.replaceAll("_", " ")}`
                  : "Live Ostrom data"}
            </p>
          </div>
        </div>
        <div className={styles.topActions}>
          <span className={styles.badge}>
            {session.mode === "demo" ? "Demo mode" : "Live API"}
          </span>
          <button
            type="button"
            className={styles.ghostBtn}
            onClick={() => {
              persist(null);
              setContracts([]);
              setConsumption([]);
              setPrices([]);
            }}
          >
            Disconnect
          </button>
        </div>
      </header>

      <main className={styles.main}>
        <section className={styles.heroLine}>
          <h1>Your electricity, dissected</h1>
          <p>
            Explore consumption patterns, spot prices, and shift opportunities
            beyond what the Ostrom app surfaces.
          </p>
        </section>

        <RangeControls
          preset={preset}
          onPreset={setPreset}
          view={view}
          onView={setView}
          loading={loading}
          label={`${format(range.start, "d MMM")} – ${format(range.end, "d MMM yyyy")}`}
        />

        {error && <div className={styles.error}>{error}</div>}

        <OverviewStrip stats={stats} />

        <section className={styles.panel}>
          <div className={styles.panelHead}>
            <h2>Consumption & price</h2>
            <p>
              {view === "hour" ? "Hourly" : "Daily"} series with estimated cost when
              prices align.
            </p>
          </div>
          <ConsumptionChart data={series} view={view} />
        </section>

        <div className={styles.gridTwo}>
          <section className={styles.panel}>
            <div className={styles.panelHead}>
              <h2>Average day profile</h2>
              <p>When you use power vs when it costs most.</p>
            </div>
            <HourlyProfile data={hours} />
          </section>

          <section className={styles.panel}>
            <div className={styles.panelHead}>
              <h2>Week × hour heatmap</h2>
              <p>Brighter cells mean higher average kWh.</p>
            </div>
            <HeatmapChart data={heat} />
          </section>
        </div>

        <InsightsPanel
          insights={insights}
          peakAt={
            stats.peakAt
              ? format(parseISO(stats.peakAt), "EEE d MMM · HH:mm")
              : null
          }
          peakKwh={stats.peakKwh}
        />
      </main>

      <footer className={styles.footer}>
        <p>
          Credentials stay in your browser session and are only forwarded to Ostrom
          via this app&apos;s proxy. Not affiliated with Ostrom.
        </p>
      </footer>
    </div>
  );
}
