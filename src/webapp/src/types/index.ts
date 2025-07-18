export interface CryptoAnalysis {
  analysis: string;
  chosen_strategies: {
    strategy_id: number;
    score: number | null;
  }[];
}

export interface Strategy {
  id: number;
  name: string;
  description: string;
  compatible_symbols: string[];
  compatible_timeframes: string[];
}

export interface TechnicalIndicator {
  name: string;
  value: number | string;
  description?: string;
}

export interface AnalysisRequest {
  symbol: string;
  timeframes: string[];
  user_prompt: string;
}
