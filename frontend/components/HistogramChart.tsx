"use client";

import {
  Bar,
  BarChart,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Histogram } from "@/lib/types";

interface HistogramChartProps {
  histogram: Histogram;
  color: string;
  // Formats an x-axis value (a bin edge). Currency or percent.
  formatX: (value: number) => string;
  // Optional vertical marker, e.g. the target quote or the zero-margin line.
  marker?: { value: number; label: string };
  height?: number;
}

interface Bin {
  center: number;
  count: number;
  x0: number;
  x1: number;
}

function buildBins(histogram: Histogram): Bin[] {
  const { bin_edges, counts } = histogram;
  const bins: Bin[] = [];
  for (let i = 0; i < counts.length; i += 1) {
    const x0 = bin_edges[i];
    const x1 = bin_edges[i + 1];
    bins.push({ x0, x1, center: (x0 + x1) / 2, count: counts[i] });
  }
  return bins;
}

export function HistogramChart({
  histogram,
  color,
  formatX,
  marker,
  height = 240,
}: HistogramChartProps) {
  const bins = buildBins(histogram);

  if (bins.length === 0) {
    return (
      <div className="grid h-40 place-items-center text-sm text-ink-500">
        No distribution data.
      </div>
    );
  }

  const domainMin = bins[0].x0;
  const domainMax = bins[bins.length - 1].x1;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart
        data={bins}
        margin={{ top: 8, right: 8, bottom: 4, left: 8 }}
        barCategoryGap={1}
      >
        <XAxis
          dataKey="center"
          type="number"
          domain={[domainMin, domainMax]}
          tickFormatter={formatX}
          tick={{ fill: "#8590a8", fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
          minTickGap={40}
        />
        <YAxis
          tick={{ fill: "#8590a8", fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          width={36}
          allowDecimals={false}
        />
        <Tooltip
          cursor={{ fill: "rgba(255,255,255,0.05)" }}
          contentStyle={{
            backgroundColor: "#0f1218",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: "0.6rem",
            color: "#e7eaf0",
            fontSize: "0.8rem",
          }}
          labelFormatter={(value) => formatX(Number(value))}
          formatter={(value: number) => [`${value} runs`, "Count"]}
        />
        {marker ? (
          <ReferenceLine
            x={marker.value}
            stroke="#f5f5f5"
            strokeDasharray="4 3"
            strokeOpacity={0.6}
            label={{
              value: marker.label,
              position: "insideTopRight",
              fill: "#c7cdd9",
              fontSize: 11,
            }}
          />
        ) : null}
        <Bar dataKey="count" radius={[2, 2, 0, 0]} isAnimationActive={false}>
          {bins.map((bin) => (
            <Cell key={bin.center} fill={color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
