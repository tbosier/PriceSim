// Small formatting helpers so numbers read consistently across the dashboard.

const usd0 = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const num0 = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

export function formatCurrency(value: number): string {
  return usd0.format(value);
}

// Compact form for the big metric cards, e.g. $6.0M.
export function formatCurrencyCompact(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(2)}M`;
  }
  if (abs >= 1_000) {
    return `$${(value / 1_000).toFixed(0)}K`;
  }
  return usd0.format(value);
}

export function formatNumber(value: number, digits = 0): string {
  if (digits === 0) {
    return num0.format(value);
  }
  return value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatPercent(fraction: number, digits = 1): string {
  return `${(fraction * 100).toFixed(digits)}%`;
}

export function formatMultiplier(value: number): string {
  return `${value.toFixed(2)}x`;
}
