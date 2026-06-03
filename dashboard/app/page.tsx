"use client";

import { useEffect, useMemo, useState } from "react";
import type { Results, History, Case } from "./types";
import { pct, ms, passRateAccent, fmtTimestamp, truncate } from "./format";
import { TrendChart, CategoryChart, DistributionChart } from "./Charts";

type Filter = "all" | "failed";

export default function Page() {
  const [results, setResults] = useState<Results | null>(null);
  const [history, setHistory] = useState<History | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("all");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [r, h] = await Promise.all([
          fetch("/results.json").then((res) => {
            if (!res.ok) throw new Error(`results.json: ${res.status}`);
            return res.json() as Promise<Results>;
          }),
          fetch("/history.json").then((res) => {
            if (!res.ok) throw new Error(`history.json: ${res.status}`);
            return res.json() as Promise<History>;
          }),
        ]);
        if (!cancelled) {
          setResults(r);
          setHistory(h);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const cases = useMemo<Case[]>(() => {
    if (!results) return [];
    return filter === "failed"
      ? results.cases.filter((c) => !c.passed)
      : results.cases;
  }, [results, filter]);

  if (error) {
    return (
      <main className="page">
        <div className="center-state">
          <div className="error-box">Failed to load data — {error}</div>
        </div>
      </main>
    );
  }

  if (!results || !history) {
    return (
      <main className="page">
        <div className="center-state">
          <div className="spinner" />
          <div>Loading reliability data…</div>
        </div>
      </main>
    );
  }

  const { meta, summary } = results;
  const accent = passRateAccent(summary.pass_rate);
  const failedCount = summary.total - summary.passed;

  return (
    <main className="page">
      {/* Header */}
      <header className="header">
        <div>
          <h1>
            <span className="dot" />
            reliabench
          </h1>
          <div className="sub">
            <span className="meta-pill">
              model <code>{meta.model}</code>
            </span>
            <span className="meta-pill">
              evalset <code>{meta.evalset}</code>
            </span>
            <span className="meta-pill">
              run <code>{meta.run_id}</code>
            </span>
          </div>
        </div>
        <div className="ts">
          Evaluated
          <br />
          {fmtTimestamp(meta.timestamp)}
        </div>
      </header>

      {/* KPI cards */}
      <section className="kpi-grid">
        <div className={`card kpi accent-${accent}`}>
          <div className="label">Pass rate</div>
          <div className="value">{pct(summary.pass_rate)}</div>
          <span className="badge">
            {accent === "green"
              ? "Healthy"
              : accent === "amber"
                ? "Watch"
                : "At risk"}
          </span>
        </div>
        <div className="card kpi">
          <div className="label">Accuracy</div>
          <div className="value">{pct(summary.accuracy)}</div>
          <div className="foot">mean case score</div>
        </div>
        <div className="card kpi">
          <div className="label">Avg latency</div>
          <div className="value">
            {Math.round(summary.avg_latency_ms)}
            <span className="unit">ms</span>
          </div>
          <div className="foot">per case</div>
        </div>
        <div className="card kpi">
          <div className="label">Total cases</div>
          <div className="value">{summary.total}</div>
          <div className="foot">
            {summary.passed} passed · {failedCount} failed
          </div>
        </div>
      </section>

      {/* Trend + Distribution */}
      <section className="charts-grid">
        <div className="card">
          <h2>Reliability trend</h2>
          <p className="card-sub">Pass rate &amp; accuracy across recent runs</p>
          <TrendChart history={history} />
        </div>
        <div className="card">
          <h2>Pass / fail</h2>
          <p className="card-sub">Latest run distribution</p>
          <DistributionChart summary={summary} />
        </div>
      </section>

      {/* Categories */}
      <section className="charts-row2">
        <div className="card">
          <h2>Pass rate by category</h2>
          <p className="card-sub">Where reliability holds up — and where it breaks</p>
          <CategoryChart summary={summary} />
        </div>
        <div className="card">
          <h2>Category breakdown</h2>
          <p className="card-sub">Passed / total per category</p>
          <div className="table-wrap">
            <table className="cases">
              <thead>
                <tr>
                  <th>Category</th>
                  <th>Passed</th>
                  <th>Rate</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(summary.categories).map(([name, c]) => (
                  <tr key={name}>
                    <td className="id">{name}</td>
                    <td>
                      {c.passed}/{c.total}
                    </td>
                    <td>{pct(c.pass_rate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Cases table */}
      <section className="card">
        <div className="table-head">
          <div>
            <h2>Cases</h2>
            <p className="card-sub" style={{ margin: 0 }}>
              {cases.length} shown of {summary.total}
            </p>
          </div>
          <div className="filter-toggle" role="tablist">
            <button
              className={filter === "all" ? "active" : ""}
              onClick={() => setFilter("all")}
            >
              All
            </button>
            <button
              className={filter === "failed" ? "active" : ""}
              onClick={() => setFilter("failed")}
            >
              Failed only
            </button>
          </div>
        </div>
        <div className="table-wrap">
          <table className="cases">
            <thead>
              <tr>
                <th>ID</th>
                <th>Category</th>
                <th>Judge</th>
                <th>Latency</th>
                <th>Result</th>
                <th>Prompt</th>
                <th>Expected</th>
                <th>Output</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                <tr key={c.id}>
                  <td className="id">{c.id}</td>
                  <td>
                    <span className="chip">{c.category}</span>
                  </td>
                  <td>
                    <span className="chip judge">{c.judge}</span>
                  </td>
                  <td className="latency">{ms(c.latency_ms)}</td>
                  <td>
                    <span className={`pf ${c.passed ? "pass" : "fail"}`}>
                      {c.passed ? "Pass" : "Fail"}
                    </span>
                  </td>
                  <td className="text">
                    <div className="truncate">{truncate(c.prompt, 140)}</div>
                  </td>
                  <td className="text">
                    <div className="truncate mono">{truncate(c.expected, 80)}</div>
                  </td>
                  <td className="text">
                    <div className="truncate mono">{truncate(c.output, 80)}</div>
                  </td>
                </tr>
              ))}
              {cases.length === 0 && (
                <tr>
                  <td colSpan={8} style={{ textAlign: "center", padding: "28px" }}>
                    No cases match this filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
