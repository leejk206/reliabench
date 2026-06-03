export interface ResultsMeta {
  model: string;
  evalset: string;
  run_id: string;
  timestamp: string;
}

export interface CategorySummary {
  total: number;
  passed: number;
  pass_rate: number;
}

export interface ResultsSummary {
  total: number;
  passed: number;
  pass_rate: number;
  accuracy: number;
  avg_latency_ms: number;
  categories: Record<string, CategorySummary>;
}

export type Judge =
  | "exact"
  | "contains"
  | "regex"
  | "json_valid"
  | "json_schema"
  | "llm"
  | string;

export interface Case {
  id: string;
  category: string;
  prompt: string;
  expected: string;
  output: string;
  passed: boolean;
  score: number;
  latency_ms: number;
  judge: Judge;
}

export interface Results {
  meta: ResultsMeta;
  summary: ResultsSummary;
  cases: Case[];
}

export interface HistoryEntry {
  run_id: string;
  timestamp: string;
  pass_rate: number;
  accuracy: number;
  avg_latency_ms: number;
}

export type History = HistoryEntry[];
