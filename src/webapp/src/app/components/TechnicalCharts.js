"use client";

import { useState, useEffect } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  TimeScale
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import 'chartjs-adapter-date-fns';

// Registrar los componentes de Chart.js
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  TimeScale
);

export default function TechnicalCharts({ symbol, timeframe }) {
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchChartData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        // En un entorno real, aquí se haría una llamada a la API para obtener los datos
        // Por ahora, generaremos datos de ejemplo
        
        // Generar fechas para el eje X (últimos 30 días)
        const dates = [];
        const ohlcData = [];
        const macdLine = [];
        const macdSignal = [];
        const macdHistogram = [];
        const rsiValues = [];
        
        const now = new Date();
        let prevClose = symbol === 'BTC' ? 65000 : symbol === 'ETH' ? 3400 : 120;
        
        for (let i = 29; i >= 0; i--) {
          const date = new Date(now);
          date.setDate(date.getDate() - i);
          dates.push(date);
          
          // Generar datos OHLC (Open, High, Low, Close) para velas japonesas
          const basePrice = symbol === 'BTC' ? 65000 : symbol === 'ETH' ? 3400 : 120;
          const trend = i / 10; // Tendencia alcista
          const volatility = Math.random() * 500 - 250; // Volatilidad
          
          const open = prevClose;
          const close = basePrice + (trend * 500) + volatility;
          const high = Math.max(open, close) + (Math.random() * 200);
          const low = Math.min(open, close) - (Math.random() * 200);
          
          ohlcData.push({
            x: date,
            o: open,
            h: high,
            l: low,
            c: close
          });
          
          prevClose = close;
          
          // Calcular MACD basado en los precios de cierre
          // En un entorno real, esto se calcularía usando los datos históricos reales
          // MACD = EMA(12) - EMA(26)
          // Signal Line = EMA(9) del MACD
          const ema12 = close * 0.15 + (close * 0.85);
          const ema26 = close * 0.075 + (close * 0.925);
          const macd = ema12 - ema26;
          const signal = macd * 0.2 + (macd * 0.8);
          const histogram = macd - signal;
          
          macdLine.push(macd);
          macdSignal.push(signal);
          macdHistogram.push(histogram);
          
          // Calcular RSI basado en los cambios de precio
          // En un entorno real, esto se calcularía usando los datos históricos reales
          // RSI = 100 - (100 / (1 + RS))
          // RS = Promedio de ganancias / Promedio de pérdidas
          const priceChange = close - open;
          const gain = priceChange > 0 ? priceChange : 0;
          const loss = priceChange < 0 ? -priceChange : 0;
          const rs = loss === 0 ? 100 : gain / loss;
          const rsi = 100 - (100 / (1 + rs));
          
          rsiValues.push(Math.max(0, Math.min(100, rsi)));
        }
        
        setChartData({
          dates,
          ohlcData,
          macdLine,
          macdSignal,
          macdHistogram,
          rsiValues
        });
        
      } catch (err) {
        console.error("Error fetching chart data:", err);
        setError("No se pudieron cargar los datos del gráfico");
      } finally {
        setLoading(false);
      }
    };
    
    if (symbol && timeframe) {
      fetchChartData();
    }
  }, [symbol, timeframe]);

  // Opciones comunes para todos los gráficos
  const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: 'rgba(255, 255, 255, 0.8)',
          font: {
            size: 12
          }
        }
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: 'rgba(255, 255, 255, 0.9)',
        bodyColor: 'rgba(255, 255, 255, 0.9)',
        borderColor: 'rgba(255, 255, 255, 0.2)',
        borderWidth: 1
      }
    },
    scales: {
      x: {
        grid: {
          color: 'rgba(255, 255, 255, 0.1)',
        },
        ticks: {
          color: 'rgba(255, 255, 255, 0.7)',
        }
      }
    }
  };

  // Configuración del gráfico de precios (velas japonesas)
  const priceChartOptions = {
    ...commonOptions,
    plugins: {
      ...commonOptions.plugins,
      title: {
        display: true,
        text: `Precio de ${symbol}`,
        color: 'rgba(255, 255, 255, 0.9)',
        font: {
          size: 16
        }
      }
    },
    scales: {
      ...commonOptions.scales,
      x: {
        type: 'time',
        time: {
          unit: 'day',
          displayFormats: {
            day: 'dd/MM'
          }
        },
        grid: {
          color: 'rgba(255, 255, 255, 0.1)',
        },
        ticks: {
          color: 'rgba(255, 255, 255, 0.7)',
        }
      },
      y: {
        grid: {
          color: 'rgba(255, 255, 255, 0.1)',
        },
        ticks: {
          color: 'rgba(255, 255, 255, 0.7)',
          callback: function(value) {
            return '$' + value.toLocaleString();
          }
        }
      }
    }
  };

  // Configuración del gráfico MACD
  const macdChartOptions = {
    ...commonOptions,
    plugins: {
      ...commonOptions.plugins,
      title: {
        display: true,
        text: 'MACD',
        color: 'rgba(255, 255, 255, 0.9)',
        font: {
          size: 16
        }
      }
    },
    scales: {
      ...commonOptions.scales,
      y: {
        grid: {
          color: 'rgba(255, 255, 255, 0.1)',
        },
        ticks: {
          color: 'rgba(255, 255, 255, 0.7)',
        }
      }
    }
  };

  // Configuración del gráfico RSI
  const rsiChartOptions = {
    ...commonOptions,
    plugins: {
      ...commonOptions.plugins,
      title: {
        display: true,
        text: 'RSI',
        color: 'rgba(255, 255, 255, 0.9)',
        font: {
          size: 16
        }
      }
    },
    scales: {
      ...commonOptions.scales,
      y: {
        grid: {
          color: 'rgba(255, 255, 255, 0.1)',
        },
        ticks: {
          color: 'rgba(255, 255, 255, 0.7)',
        },
        min: 0,
        max: 100,
        afterDraw: (chart) => {
          // Dibujar líneas de referencia para RSI (30 y 70)
          const ctx = chart.ctx;
          const yAxis = chart.scales.y;
          const canvas = chart.canvas;
          
          ctx.save();
          ctx.beginPath();
          ctx.moveTo(yAxis.left, yAxis.getPixelForValue(30));
          ctx.lineTo(yAxis.right, yAxis.getPixelForValue(30));
          ctx.lineWidth = 1;
          ctx.strokeStyle = 'rgba(255, 0, 0, 0.5)';
          ctx.stroke();
          
          ctx.beginPath();
          ctx.moveTo(yAxis.left, yAxis.getPixelForValue(70));
          ctx.lineTo(yAxis.right, yAxis.getPixelForValue(70));
          ctx.lineWidth = 1;
          ctx.strokeStyle = 'rgba(0, 255, 0, 0.5)';
          ctx.stroke();
          
          ctx.restore();
        }
      }
    }
  };

  // Datos para el gráfico de precios
  const priceChartData = chartData ? {
    labels: chartData.dates,
    datasets: [
      {
        label: `${symbol} Precio`,
        data: chartData.ohlcData.map(item => item.c), // Usar precio de cierre
        borderColor: 'rgba(75, 192, 192, 1)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        fill: true,
        tension: 0.4
      },
      {
        label: `${symbol} Máximo`,
        data: chartData.ohlcData.map(item => item.h), // Usar precio máximo
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 1,
        pointRadius: 0,
        borderDash: [5, 5],
        fill: false
      },
      {
        label: `${symbol} Mínimo`,
        data: chartData.ohlcData.map(item => item.l), // Usar precio mínimo
        borderColor: 'rgba(255, 99, 132, 1)',
        borderWidth: 1,
        pointRadius: 0,
        borderDash: [5, 5],
        fill: false
      }
    ]
  } : null;

  // Datos para el gráfico MACD
  const macdChartData = chartData ? {
    labels: chartData.dates,
    datasets: [
      {
        label: 'MACD Line',
        data: chartData.macdLine,
        borderColor: 'rgba(75, 192, 192, 1)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        borderWidth: 2,
        tension: 0.4,
        yAxisID: 'y'
      },
      {
        label: 'Signal Line',
        data: chartData.macdSignal,
        borderColor: 'rgba(255, 99, 132, 1)',
        backgroundColor: 'rgba(255, 99, 132, 0.2)',
        borderWidth: 2,
        tension: 0.4,
        yAxisID: 'y'
      },
      {
        label: 'Histogram',
        data: chartData.macdHistogram,
        borderColor: 'rgba(153, 102, 255, 1)',
        backgroundColor: function(context) {
          const value = context.dataset.data[context.dataIndex];
          return value >= 0 ? 'rgba(75, 192, 192, 0.5)' : 'rgba(255, 99, 132, 0.5)';
        },
        borderWidth: 0,
        type: 'bar',
        yAxisID: 'y'
      }
    ]
  } : null;

  // Datos para el gráfico RSI
  const rsiChartData = chartData ? {
    labels: chartData.dates,
    datasets: [
      {
        label: 'RSI',
        data: chartData.rsiValues,
        borderColor: 'rgba(255, 159, 64, 1)',
        backgroundColor: 'rgba(255, 159, 64, 0.2)',
        borderWidth: 2,
        tension: 0.4
      }
    ]
  } : null;

  if (loading) {
    return (
      <div className="bg-gray-800/60 p-6 rounded-lg shadow-lg flex flex-col items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500 mb-4"></div>
        <p className="text-gray-400">Cargando gráficos para {symbol}...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/30 p-6 rounded-lg shadow-lg mb-6">
        <h3 className="text-xl font-bold mb-4 text-red-400">Error</h3>
        <p className="text-white">{error}</p>
      </div>
    );
  }

  if (!chartData) {
    return (
      <div className="bg-gray-800/60 p-6 rounded-lg shadow-lg mb-6">
        <p className="text-gray-400">No hay datos disponibles para mostrar.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Gráfico de precios */}
      <div className="bg-gray-800/60 p-4 rounded-lg shadow-lg">
        <div className="h-64">
          <Line options={priceChartOptions} data={priceChartData} />
        </div>
      </div>
      
      {/* Gráfico MACD */}
      <div className="bg-gray-800/60 p-4 rounded-lg shadow-lg">
        <div className="h-48">
          <Line options={macdChartOptions} data={macdChartData} />
        </div>
      </div>
      
      {/* Gráfico RSI */}
      <div className="bg-gray-800/60 p-4 rounded-lg shadow-lg">
        <div className="h-48">
          <Line options={rsiChartOptions} data={rsiChartData} />
        </div>
      </div>
    </div>
  );
}
