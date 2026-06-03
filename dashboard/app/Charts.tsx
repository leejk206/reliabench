"use client";

import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { History, ResultsSummary } from "./types";
import { pctValue } from "./format";

const AXIS = "#6b7488";
const GRID = "#232a39";
const ACCENT = "#5b8cff";
const ACCENT2 = "#3ecf8e";
const GREEN = "#3ecf8e";
const RED = "#f56b6b";

function pctTick(v: number) {
  return `${v}%`;
}

export function TrendChart({ history }: { history: History }) {
  const data = history.map((h) => ({
    run: h.run_id,
    pass_rate: pctValue(h.pass_rate),
    accuracy: pctValue(h.accuracy),
  }));
  return (
    <div className="chart-box">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="run" stroke={AXIS} tick={{ fontSize: 12 }} tickLine={false} />
          <YAxis
            domain={[0, 100]}
            stroke={AXIS}
            tick={{ fontSize: 12 }}
            tickFormatter={pctTick}
            tickLine={false}
            width={44}
          />
          <Tooltip
            formatter={(v: number) => `${v}%`}
            contentStyle={{ background: "#131722", border: "1px solid #232a39" }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line
            type="monotone"
            dataKey="pass_rate"
            name="Pass rate"
            stroke={ACCENT}
            strokeWidth={2.5}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
          <Line
            type="monotone"
            dataKey="accuracy"
            name="Accuracy"
            stroke={ACCENT2}
            strokeWidth={2.5}
            strokeDasharray="5 4"
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function CategoryChart({ summary }: { summary: ResultsSummary }) {
  const data = Object.entries(summary.categories).map(([name, c]) => ({
    category: name,
    pass_rate: pctValue(c.pass_rate),
    passed: c.passed,
    total: c.total,
  }));
  return (
    <div className="chart-box short">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="category" stroke={AXIS} tick={{ fontSize: 12 }} tickLine={false} />
          <YAxis
            domain={[0, 100]}
            stroke={AXIS}
            tick={{ fontSize: 12 }}
            tickFormatter={pctTick}
            tickLine={false}
            width={44}
          />
          <Tooltip
            cursor={{ fill: "rgba(91,140,255,0.08)" }}
            formatter={(v: number) => [`${v}%`, "Pass rate"]}
            contentStyle={{ background: "#131722", border: "1px solid #232a39" }}
          />
          <Bar dataKey="pass_rate" name="Pass rate" radius={[6, 6, 0, 0]} maxBarSize={64}>
            {data.map((d, i) => (
              <Cell
                key={i}
                fill={
                  d.pass_rate >= 80 ? GREEN : d.pass_rate >= 60 ? "#f5b15b" : RED
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function DistributionChart({ summary }: { summary: ResultsSummary }) {
  const failed = summary.total - summary.passed;
  const data = [
    { name: "Passed", value: summary.passed, color: GREEN },
    { name: "Failed", value: failed, color: RED },
  ];
  return (
    <div className="chart-box short">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={56}
            outerRadius={88}
            paddingAngle={2}
            stroke="none"
          >
            {data.map((d, i) => (
              <Cell key={i} fill={d.color} />
            ))}
          </Pie>
          <Tooltip
            formatter={(v: number, n: string) => [`${v} cases`, n]}
            contentStyle={{ background: "#131722", border: "1px solid #232a39" }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
