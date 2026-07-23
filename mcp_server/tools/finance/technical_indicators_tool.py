"""Technical Indicators Tool - Calculate technical indicators for stocks."""

from __future__ import annotations

import logging
from typing import Any, Optional

import numpy as np

from mcp_server.tools.base import BaseTool
from mcp_server.tools.finance.advanced_schemas import (
    TECHNICAL_INDICATORS_INPUT_SCHEMA,
    TECHNICAL_INDICATORS_OUTPUT_SCHEMA,
)
from mcp_server.tools.finance.advanced_exceptions import TechnicalIndicatorsError
from mcp_server.services.finance import FinanceService, FinanceServiceError, SymbolNotFoundError

logger = logging.getLogger(__name__)


class TechnicalIndicatorsCalculator:
    """Calculator for technical indicators.
    
    Provides static methods for calculating various technical indicators
    using numpy for efficient computation.
    """

    def _calculate_sma(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Simple Moving Average."""
        if len(prices) < period:
            return np.full(len(prices), np.nan)
        sma = np.convolve(prices, np.ones(period) / period, mode='valid')
        return np.concatenate([np.full(period - 1, np.nan), sma])

    def _calculate_ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return np.full(len(prices), np.nan)
        alpha = 2.0 / (period + 1)
        ema = np.full(len(prices), np.nan)
        ema[period - 1] = np.mean(prices[:period])
        for i in range(period, len(prices)):
            ema[i] = alpha * prices[i] + (1 - alpha) * ema[i - 1]
        return ema

    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate Relative Strength Index."""
        if len(prices) < period + 1:
            return np.full(len(prices), np.nan)
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.full(len(prices), np.nan)
        avg_loss = np.full(len(prices), np.nan)
        
        avg_gain[period] = np.mean(gains[:period])
        avg_loss[period] = np.mean(losses[:period])
        
        for i in range(period + 1, len(prices)):
            avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gains[i - 1]) / period
            avg_loss[i] = (avg_loss[i - 1] * (period - 1) + losses[i - 1]) / period
        
        rs = np.where(avg_loss != 0, avg_gain / avg_loss, np.inf)
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_macd(self, prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """Calculate MACD (Moving Average Convergence Divergence)."""
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        macd_line = ema_fast - ema_slow
        signal_line = self._calculate_ema(macd_line, signal)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def _calculate_bollinger_bands(self, prices: np.ndarray, period: int = 20, std_dev: float = 2) -> tuple:
        """Calculate Bollinger Bands."""
        sma = self._calculate_sma(prices, period)
        rolling_std = np.full(len(prices), np.nan)
        
        for i in range(period - 1, len(prices)):
            rolling_std[i] = np.std(prices[i - period + 1:i + 1])
        
        upper = sma + (rolling_std * std_dev)
        lower = sma - (rolling_std * std_dev)
        bandwidth = (upper - lower) / sma
        percent_b = (prices - lower) / (upper - lower)
        
        return upper, sma, lower, bandwidth, percent_b

    def _calculate_atr(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate Average True Range."""
        if len(high) < period + 1:
            return np.full(len(high), np.nan)
        
        tr1 = high - low
        tr2 = np.abs(high - np.roll(close, 1))
        tr3 = np.abs(low - np.roll(close, 1))
        tr1[0] = 0
        tr2[0] = 0
        tr3[0] = 0
        
        true_range = np.maximum(tr1, np.maximum(tr2, tr3))
        atr = self._calculate_sma(true_range, period)
        return atr

    def _calculate_vwap(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Calculate Volume Weighted Average Price."""
        typical_price = (high + low + close) / 3
        cumulative_tpv = np.cumsum(typical_price * volume)
        cumulative_vol = np.cumsum(volume)
        vwap = cumulative_tpv / cumulative_vol
        return vwap

    def _find_support_resistance(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, window: int = 20) -> dict:
        """Find support and resistance levels."""
        recent_high = high[-window:]
        recent_low = low[-window:]
        current_price = close[-1]
        
        # Find local maxima/minima
        resistance_levels = []
        support_levels = []
        
        for i in range(1, len(recent_high) - 1):
            if recent_high[i] > recent_high[i-1] and recent_high[i] > recent_high[i+1]:
                resistance_levels.append(recent_high[i])
            if recent_low[i] < recent_low[i-1] and recent_low[i] < recent_low[i+1]:
                support_levels.append(recent_low[i])
        
        # Filter and sort
        resistance_levels = sorted(set([round(r, 2) for r in resistance_levels if r > current_price]))
        support_levels = sorted(set([round(s, 2) for s in support_levels if s < current_price]), reverse=True)
        
        nearest_resistance = resistance_levels[0] if resistance_levels else None
        nearest_support = support_levels[0] if support_levels else None
        
        return {
            "support_levels": support_levels[:5],
            "resistance_levels": resistance_levels[:5],
            "current_price": round(current_price, 2),
            "nearest_support": nearest_support,
            "nearest_resistance": nearest_resistance,
        }

    def _detect_trend(self, close: np.ndarray) -> dict:
        """Detect trend direction and strength."""
        if len(close) < 50:
            return {"direction": "unknown", "strength": 0, "duration_days": 0, "key_levels": []}
        
        sma_20 = self._calculate_sma(close, 20)
        sma_50 = self._calculate_sma(close, 50)
        
        current_price = close[-1]
        sma_20_current = sma_20[-1]
        sma_50_current = sma_50[-1]
        
        if np.isnan(sma_20_current) or np.isnan(sma_50_current):
            return {"direction": "unknown", "strength": 0, "duration_days": 0, "key_levels": []}
        
        # Determine trend
        if current_price > sma_20_current > sma_50_current:
            direction = "uptrend"
        elif current_price < sma_20_current < sma_50_current:
            direction = "downtrend"
        else:
            direction = "sideways"
        
        # Strength based on distance from MAs
        if direction == "uptrend":
            strength = min((current_price - sma_50_current) / sma_50_current, 1.0)
        elif direction == "downtrend":
            strength = min((sma_50_current - current_price) / sma_50_current, 1.0)
        else:
            strength = 1 - abs(current_price - sma_50_current) / sma_50_current
            strength = max(0, min(strength, 1))
        
        # Duration (simplified)
        duration = 0
        for i in range(len(close) - 1, 0, -1):
            if direction == "uptrend" and close[i] > sma_50[i]:
                duration += 1
            elif direction == "downtrend" and close[i] < sma_50[i]:
                duration += 1
            else:
                break
        
        return {
            "direction": direction,
            "strength": round(strength, 3),
            "duration_days": duration,
            "key_levels": [round(sma_20_current, 2), round(sma_50_current, 2)],
        }

    def _detect_crossovers(self, close: np.ndarray, fast_periods: list, slow_periods: list) -> list:
        """Detect SMA crossovers (golden/death crosses)."""
        crossovers = []
        
        for fast, slow in zip(fast_periods, slow_periods):
            sma_fast = self._calculate_sma(close, fast)
            sma_slow = self._calculate_sma(close, slow)
            
            for i in range(1, len(close)):
                if np.isnan(sma_fast[i]) or np.isnan(sma_slow[i]) or np.isnan(sma_fast[i-1]) or np.isnan(sma_slow[i-1]):
                    continue
                
                prev_fast, prev_slow = sma_fast[i-1], sma_slow[i-1]
                curr_fast, curr_slow = sma_fast[i], sma_slow[i]
                
                if prev_fast < prev_slow and curr_fast > curr_slow:
                    crossovers.append({
                        "date": f"day_{i}",  # Would be actual date in real impl
                        "fast_period": fast,
                        "slow_period": slow,
                        "crossover_type": "golden_cross",
                    })
                elif prev_fast > prev_slow and curr_fast < curr_slow:
                    crossovers.append({
                        "date": f"day_{i}",
                        "fast_period": fast,
                        "slow_period": slow,
                        "crossover_type": "death_cross",
                    })
        
        return crossovers


class TechnicalIndicatorsTool(BaseTool):
    """Tool for calculating technical indicators.

    Supports multiple indicators:
    - SMA (Simple Moving Average)
    - EMA (Exponential Moving Average)
    - RSI (Relative Strength Index)
    - MACD (Moving Average Convergence Divergence)
    - Bollinger Bands
    - ATR (Average True Range)
    - VWAP (Volume Weighted Average Price)
    - Moving Average Crossovers
    - Support/Resistance Levels
    - Trend Detection

    Uses Finance Service with automatic provider failover.
    """

    name = "technical_indicators"
    description = "Calculate technical indicators for stocks: SMA, EMA, RSI, MACD, Bollinger Bands, ATR, VWAP, crossovers, support/resistance, trend"
    tags = ["finance", "stocks", "technical-analysis", "indicators", "trading"]
    version = "1.0.0"
    author = "ToolBridge"

    def __init__(self, finance_service: Optional[Any] = None, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._finance_service: Optional[FinanceService] = finance_service
        self._service_initialized = finance_service is not None

    def set_finance_service(self, service: FinanceService) -> None:
        """Set the finance service (for dependency injection)."""
        self._finance_service = finance_service
        self._service_initialized = True

    def get_input_schema(self) -> dict[str, Any]:
        return TECHNICAL_INDICATORS_INPUT_SCHEMA

    def get_output_schema(self) -> dict[str, Any] | None:
        return TECHNICAL_INDICATORS_OUTPUT_SCHEMA

    def _calculate_sma(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Simple Moving Average."""
        if len(prices) < period:
            return np.full(len(prices), np.nan)
        sma = np.convolve(prices, np.ones(period) / period, mode='valid')
        return np.concatenate([np.full(period - 1, np.nan), sma])

    def _calculate_ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return np.full(len(prices), np.nan)
        alpha = 2.0 / (period + 1)
        ema = np.full(len(prices), np.nan)
        ema[period - 1] = np.mean(prices[:period])
        for i in range(period, len(prices)):
            ema[i] = alpha * prices[i] + (1 - alpha) * ema[i - 1]
        return ema

    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate Relative Strength Index."""
        if len(prices) < period + 1:
            return np.full(len(prices), np.nan)
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.full(len(prices), np.nan)
        avg_loss = np.full(len(prices), np.nan)
        
        avg_gain[period] = np.mean(gains[:period])
        avg_loss[period] = np.mean(losses[:period])
        
        for i in range(period + 1, len(prices)):
            avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gains[i - 1]) / period
            avg_loss[i] = (avg_loss[i - 1] * (period - 1) + losses[i - 1]) / period
        
        rs = np.where(avg_loss != 0, avg_gain / avg_loss, np.inf)
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_macd(self, prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """Calculate MACD (Moving Average Convergence Divergence)."""
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        macd_line = ema_fast - ema_slow
        signal_line = self._calculate_ema(macd_line, signal)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def _calculate_bollinger_bands(self, prices: np.ndarray, period: int = 20, std_dev: float = 2) -> tuple:
        """Calculate Bollinger Bands."""
        sma = self._calculate_sma(prices, period)
        rolling_std = np.full(len(prices), np.nan)
        
        for i in range(period - 1, len(prices)):
            rolling_std[i] = np.std(prices[i - period + 1:i + 1])
        
        upper = sma + (rolling_std * std_dev)
        lower = sma - (rolling_std * std_dev)
        bandwidth = (upper - lower) / sma
        percent_b = (prices - lower) / (upper - lower)
        
        return upper, sma, lower, bandwidth, percent_b

    def _calculate_atr(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate Average True Range."""
        if len(high) < period + 1:
            return np.full(len(high), np.nan)
        
        tr1 = high - low
        tr2 = np.abs(high - np.roll(close, 1))
        tr3 = np.abs(low - np.roll(close, 1))
        tr1[0] = 0
        tr2[0] = 0
        tr3[0] = 0
        
        true_range = np.maximum(tr1, np.maximum(tr2, tr3))
        atr = self._calculate_sma(true_range, period)
        return atr

    def _calculate_vwap(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Calculate Volume Weighted Average Price."""
        typical_price = (high + low + close) / 3
        cumulative_tpv = np.cumsum(typical_price * volume)
        cumulative_vol = np.cumsum(volume)
        vwap = cumulative_tpv / cumulative_vol
        return vwap

    def _find_support_resistance(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, window: int = 20) -> dict:
        """Find support and resistance levels."""
        recent_high = high[-window:]
        recent_low = low[-window:]
        current_price = close[-1]
        
        # Find local maxima/minima
        resistance_levels = []
        support_levels = []
        
        for i in range(1, len(recent_high) - 1):
            if recent_high[i] > recent_high[i-1] and recent_high[i] > recent_high[i+1]:
                resistance_levels.append(recent_high[i])
            if recent_low[i] < recent_low[i-1] and recent_low[i] < recent_low[i+1]:
                support_levels.append(recent_low[i])
        
        # Filter and sort
        resistance_levels = sorted(set([round(r, 2) for r in resistance_levels if r > current_price]))
        support_levels = sorted(set([round(s, 2) for s in support_levels if s < current_price]), reverse=True)
        
        nearest_resistance = resistance_levels[0] if resistance_levels else None
        nearest_support = support_levels[0] if support_levels else None
        
        return {
            "support_levels": support_levels[:5],
            "resistance_levels": resistance_levels[:5],
            "current_price": round(current_price, 2),
            "nearest_support": nearest_support,
            "nearest_resistance": nearest_resistance,
        }

    def _detect_trend(self, close: np.ndarray) -> dict:
        """Detect trend direction and strength."""
        if len(close) < 50:
            return {"direction": "unknown", "strength": 0, "duration_days": 0, "key_levels": []}
        
        sma_20 = self._calculate_sma(close, 20)
        sma_50 = self._calculate_sma(close, 50)
        
        current_price = close[-1]
        sma_20_current = sma_20[-1]
        sma_50_current = sma_50[-1]
        
        if np.isnan(sma_20_current) or np.isnan(sma_50_current):
            return {"direction": "unknown", "strength": 0, "duration_days": 0, "key_levels": []}
        
        # Determine trend
        if current_price > sma_20_current > sma_50_current:
            direction = "uptrend"
        elif current_price < sma_20_current < sma_50_current:
            direction = "downtrend"
        else:
            direction = "sideways"
        
        # Strength based on distance from MAs
        if direction == "uptrend":
            strength = min((current_price - sma_50_current) / sma_50_current, 1.0)
        elif direction == "downtrend":
            strength = min((sma_50_current - current_price) / sma_50_current, 1.0)
        else:
            strength = 1 - abs(current_price - sma_50_current) / sma_50_current
            strength = max(0, min(strength, 1))
        
        # Duration (simplified)
        duration = 0
        for i in range(len(close) - 1, 0, -1):
            if direction == "uptrend" and close[i] > sma_50[i]:
                duration += 1
            elif direction == "downtrend" and close[i] < sma_50[i]:
                duration += 1
            else:
                break
        
        return {
            "direction": direction,
            "strength": round(strength, 3),
            "duration_days": duration,
            "key_levels": [round(sma_20_current, 2), round(sma_50_current, 2)],
        }

    def _detect_crossovers(self, close: np.ndarray, fast_periods: list, slow_periods: list) -> list:
        """Detect SMA crossovers (golden/death crosses)."""
        crossovers = []
        
        for fast, slow in zip(fast_periods, slow_periods):
            sma_fast = self._calculate_sma(close, fast)
            sma_slow = self._calculate_sma(close, slow)
            
            for i in range(1, len(close)):
                if np.isnan(sma_fast[i]) or np.isnan(sma_slow[i]) or np.isnan(sma_fast[i-1]) or np.isnan(sma_slow[i-1]):
                    continue
                
                prev_fast, prev_slow = sma_fast[i-1], sma_slow[i-1]
                curr_fast, curr_slow = sma_fast[i], sma_slow[i]
                
                if prev_fast < prev_slow and curr_fast > curr_slow:
                    crossovers.append({
                        "date": f"day_{i}",  # Would be actual date in real impl
                        "fast_period": fast,
                        "slow_period": slow,
                        "crossover_type": "golden_cross",
                    })
                elif prev_fast > prev_slow and curr_fast < curr_slow:
                    crossovers.append({
                        "date": f"day_{i}",
                        "fast_period": fast,
                        "slow_period": slow,
                        "crossover_type": "death_cross",
                    })
        
        return crossovers


class TechnicalIndicatorsTool(BaseTool):
    """Tool for calculating technical indicators.

    Supports multiple indicators:
    - SMA (Simple Moving Average)
    - EMA (Exponential Moving Average)
    - RSI (Relative Strength Index)
    - MACD (Moving Average Convergence Divergence)
    - Bollinger Bands
    - ATR (Average True Range)
    - VWAP (Volume Weighted Average Price)
    - Moving Average Crossovers
    - Support/Resistance Levels
    - Trend Detection

    Uses Finance Service with automatic provider failover.
    """

    name = "technical_indicators"
    description = "Calculate technical indicators for stocks: SMA, EMA, RSI, MACD, Bollinger Bands, ATR, VWAP, crossovers, support/resistance, trend"
    tags = ["finance", "stocks", "technical-analysis", "indicators", "trading"]
    version = "1.0.0"
    author = "ToolBridge"

    def __init__(self, finance_service: Optional[Any] = None, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._finance_service: Optional[FinanceService] = finance_service
        self._service_initialized = finance_service is not None
        self._calculator = TechnicalIndicatorsCalculator()

    # Delegate calculator methods for testing
    def _calculate_sma(self, prices: np.ndarray, period: int) -> np.ndarray:
        return self._calculator._calculate_sma(prices, period)

    def _calculate_ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        return self._calculator._calculate_ema(prices, period)

    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        return self._calculator._calculate_rsi(prices, period)

    def _calculate_macd(self, prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        return self._calculator._calculate_macd(prices, fast, slow, signal)

    def _calculate_bollinger_bands(self, prices: np.ndarray, period: int = 20, std_dev: float = 2) -> tuple:
        return self._calculator._calculate_bollinger_bands(prices, period, std_dev)

    def _calculate_atr(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        return self._calculator._calculate_atr(high, low, close, period)

    def _calculate_vwap(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        return self._calculator._calculate_vwap(high, low, close, volume)

    def _find_support_resistance(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, window: int = 20) -> dict:
        return self._calculator._find_support_resistance(high, low, close, window)

    def _detect_trend(self, close: np.ndarray) -> dict:
        return self._calculator._detect_trend(close)

    def _detect_crossovers(self, close: np.ndarray, fast_periods: list, slow_periods: list) -> list:
        return self._calculator._detect_crossovers(close, fast_periods, slow_periods)

    def set_finance_service(self, service: FinanceService) -> None:
        """Set the finance service (for dependency injection)."""
        self._finance_service = finance_service
        self._service_initialized = True

    def get_input_schema(self) -> dict[str, Any]:
        return TECHNICAL_INDICATORS_INPUT_SCHEMA

    def get_output_schema(self) -> dict[str, Any] | None:
        return TECHNICAL_INDICATORS_OUTPUT_SCHEMA

    async def execute(self, arguments: dict[str, Any]) -> Any:
        """Execute technical indicators calculation."""
        if not self._service_initialized or self._finance_service is None:
            raise FinanceServiceError("Finance service not initialized. Set finance_service before executing.")

        symbol = arguments["symbol"].upper()
        indicators = arguments["indicators"]
        period = arguments.get("period", "3mo")
        interval = arguments.get("interval", "1d")
        sma_periods = arguments.get("sma_periods", [20, 50, 200])
        ema_periods = arguments.get("ema_periods", [12, 26])
        rsi_period = arguments.get("rsi_period", 14)
        macd_fast = arguments.get("macd_fast", 12)
        macd_slow = arguments.get("macd_slow", 26)
        macd_signal = arguments.get("macd_signal", 9)
        bb_period = arguments.get("bb_period", 20)
        bb_std = arguments.get("bb_std", 2)

        logger.info(f"Calculating {indicators} for {symbol} (period: {period}, interval: {interval})")

        try:
            # Fetch historical data from finance service
            hist_data = await self._finance_service.get_historical_prices(
                symbol=symbol,
                period=period,
                interval=interval,
            )

            # Extract price data
            data_points = hist_data.get("data", [])
            if not data_points:
                return {
                    "symbol": symbol,
                    "name": hist_data.get("name", f"{symbol} Corporation"),
                    "period": period,
                    "interval": interval,
                    "indicators": {},
                    "source": "yahoo_finance",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            # Convert to numpy arrays
            dates = [dp.get("date") for dp in data_points]
            opens = np.array([dp.get("open", 0) for dp in data_points])
            highs = np.array([dp.get("high", 0) for dp in data_points])
            lows = np.array([dp.get("low", 0) for dp in data_points])
            closes = np.array([dp.get("close", 0) for dp in data_points])
            volumes = np.array([dp.get("volume", 0) for dp in data_points])
            adjusted_closes = np.array([dp.get("adjusted_close", dp.get("close", 0)) for dp in data_points])

            # Use adjusted close for calculations
            prices = adjusted_closes

            from datetime import datetime, timezone

            response = {
                "symbol": symbol,
                "name": hist_data.get("name", f"{symbol} Corporation"),
                "period": period,
                "interval": interval,
                "indicators": {},
                "source": "yahoo_finance",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Calculate requested indicators
            if "sma" in indicators:
                response["indicators"]["sma"] = {}
                for p in sma_periods:
                    sma_values = self._calculate_sma(prices, p)
                    response["indicators"]["sma"][str(p)] = [
                        {"date": dates[i], "value": float(sma_values[i])} 
                        for i in range(len(sma_values)) if not np.isnan(sma_values[i])
                    ]

            if "ema" in indicators:
                response["indicators"]["ema"] = {}
                for p in ema_periods:
                    ema_values = self._calculate_ema(prices, p)
                    response["indicators"]["ema"][str(p)] = [
                        {"date": dates[i], "value": float(ema_values[i])} 
                        for i in range(len(ema_values)) if not np.isnan(ema_values[i])
                    ]

            if "rsi" in indicators:
                rsi_values = self._calculate_rsi(prices, rsi_period)
                response["indicators"]["rsi"] = [
                    {"date": dates[i], "value": float(rsi_values[i])} 
                    for i in range(len(rsi_values)) if not np.isnan(rsi_values[i])
                ]

            if "macd" in indicators:
                macd_line, signal_line, histogram = self._calculate_macd(prices, macd_fast, macd_slow, macd_signal)
                response["indicators"]["macd"] = [
                    {"date": dates[i], "macd": float(macd_line[i]), "signal": float(signal_line[i]), "histogram": float(histogram[i])}
                    for i in range(len(macd_line)) if not np.isnan(macd_line[i])
                ]

            if "bollinger_bands" in indicators:
                upper, middle, lower, bandwidth, percent_b = self._calculate_bollinger_bands(prices, bb_period, bb_std)
                response["indicators"]["bollinger_bands"] = [
                    {"date": dates[i], "upper": float(upper[i]), "middle": float(middle[i]), "lower": float(lower[i]), "bandwidth": float(bandwidth[i]), "percent_b": float(percent_b[i])}
                    for i in range(len(upper)) if not np.isnan(upper[i])
                ]

            if "atr" in indicators:
                atr_values = self._calculate_atr(highs, lows, closes, 14)
                response["indicators"]["atr"] = [
                    {"date": dates[i], "value": float(atr_values[i])} 
                    for i in range(len(atr_values)) if not np.isnan(atr_values[i])
                ]

            if "vwap" in indicators:
                vwap_values = self._calculate_vwap(highs, lows, closes, volumes)
                response["indicators"]["vwap"] = [
                    {"date": dates[i], "value": float(vwap_values[i])} 
                    for i in range(len(vwap_values)) if not np.isnan(vwap_values[i])
                ]

            if "sma_crossover" in indicators:
                crossovers = self._detect_crossovers(prices, sma_periods[:2], sma_periods[1:3])
                response["indicators"]["sma_crossovers"] = crossovers

            if "support_resistance" in indicators:
                sr = self._find_support_resistance(highs, lows, closes)
                response["indicators"]["support_resistance"] = sr

            if "trend" in indicators:
                trend = self._detect_trend(closes)
                response["indicators"]["trend"] = trend

            logger.info(f"Technical indicators calculated for {symbol}")
            return response

        except SymbolNotFoundError:
            logger.warning(f"Symbol not found: {symbol}")
            raise
        except FinanceServiceError as e:
            logger.error(f"Finance service error for {symbol}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calculating indicators for {symbol}: {e}")
            raise TechnicalIndicatorsError(symbol, "all", f"Unexpected error: {e}") from e

    async def execute_async(self, arguments: dict[str, Any]) -> Any:
        return await self.execute(arguments)