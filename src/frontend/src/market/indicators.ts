export function smaSeries(values: number[], period: number): (number | null)[] {
  const out: (number | null)[] = new Array(values.length).fill(null);
  let sum = 0;
  for (let i = 0; i < values.length; i++) {
    sum += values[i];
    if (i >= period) sum -= values[i - period];
    if (i >= period - 1) out[i] = sum / period;
  }
  return out;
}

export function lastSma(values: number[], period: number): number | null {
  const series = smaSeries(values, period);
  return series[series.length - 1];
}

// Wilder-smoothed RSI.
export function rsi(values: number[], period = 14): number | null {
  if (values.length <= period) return null;
  let gain = 0;
  let loss = 0;
  for (let i = 1; i <= period; i++) {
    const d = values[i] - values[i - 1];
    gain += Math.max(d, 0);
    loss += Math.max(-d, 0);
  }
  let avgGain = gain / period;
  let avgLoss = loss / period;
  for (let i = period + 1; i < values.length; i++) {
    const d = values[i] - values[i - 1];
    avgGain = (avgGain * (period - 1) + Math.max(d, 0)) / period;
    avgLoss = (avgLoss * (period - 1) + Math.max(-d, 0)) / period;
  }
  if (avgLoss === 0) return 100;
  return 100 - 100 / (1 + avgGain / avgLoss);
}

export type TrendSignal = 'bullish' | 'bearish' | 'neutral';

export function trendSignal(
  price: number,
  sma50: number | null,
  sma200: number | null,
): TrendSignal {
  if (sma50 == null || sma200 == null) return 'neutral';
  if (price > sma50 && sma50 > sma200) return 'bullish';
  if (price < sma50 && sma50 < sma200) return 'bearish';
  return 'neutral';
}

export function rsiLabel(r: number | null): { text: string; tone: 'up' | 'down' | 'flat' } {
  if (r == null) return { text: '—', tone: 'flat' };
  if (r >= 70) return { text: 'Overbought', tone: 'down' };
  if (r <= 30) return { text: 'Oversold', tone: 'up' };
  return { text: 'Neutral', tone: 'flat' };
}
