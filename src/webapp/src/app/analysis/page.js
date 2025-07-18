"use client";

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { generateAnalysis, getAvailableSymbols, getAvailableTimeframes } from '../../lib/api';
import TechnicalCharts from '../components/TechnicalCharts';

export default function AnalysisPage() {
  const [activeTab, setActiveTab] = useState('market');
  const [selectedCrypto, setSelectedCrypto] = useState(null);
  const [timeframe, setTimeframe] = useState('1d');
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState(null);
  const [availableTimeframes, setAvailableTimeframes] = useState(['1h', '4h', '1d', '1w', '1m']);
  
  // Cargar timeframes disponibles
  useEffect(() => {
    const loadTimeframes = async () => {
      try {
        const timeframes = await getAvailableTimeframes();
        setAvailableTimeframes(timeframes);
      } catch (err) {
        console.error("Error loading timeframes:", err);
      }
    };
    
    loadTimeframes();
  }, []);
  
  // Datos de criptomonedas
  const cryptoData = [
    { 
      id: 'bitcoin', 
      name: 'Bitcoin', 
      symbol: 'BTC', 
      price: 65432.10, 
      change24h: 2.34,
      marketCap: 1258000000000,
      volume24h: 28500000000,
      supply: 19250000,
      ath: 69000,
      athDate: '2021-11-10',
      sentiment: 'bullish',
      riskLevel: 'medium'
    },
    { 
      id: 'ethereum', 
      name: 'Ethereum', 
      symbol: 'ETH', 
      price: 3456.78, 
      change24h: 1.23,
      marketCap: 415000000000,
      volume24h: 12800000000,
      supply: 120250000,
      ath: 4860,
      athDate: '2021-11-16',
      sentiment: 'bullish',
      riskLevel: 'medium'
    },
    { 
      id: 'solana', 
      name: 'Solana', 
      symbol: 'SOL', 
      price: 123.45, 
      change24h: 5.67,
      marketCap: 53000000000,
      volume24h: 2100000000,
      supply: 430000000,
      ath: 260,
      athDate: '2021-11-06',
      sentiment: 'very bullish',
      riskLevel: 'high'
    }
  ];

  // Simular análisis (para demostración)
  const fetchAnalysis = async (crypto, tf) => {
    setLoading(true);
    setError(null);
    
    try {
      // Simular tiempo de carga
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // Generar análisis simulado basado en la criptomoneda y el timeframe
      let sentiment, recommendation, confidence, analysisText;
      
      // Determinar sentimiento basado en la criptomoneda
      if (crypto.symbol === 'BTC') {
        sentiment = 'Alcista';
        recommendation = 'Acumular';
        confidence = 65;
        analysisText = `El análisis técnico de Bitcoin (BTC) en timeframe ${tf} muestra señales alcistas. 
        
Los indicadores técnicos como el RSI (58) sugieren un impulso moderado, mientras que el MACD muestra una divergencia positiva. El precio se mantiene por encima de las medias móviles de 50 y 200 períodos, lo que confirma la tendencia alcista a medio plazo.

Se observa un patrón de triángulo ascendente en formación, lo que podría indicar una continuación del movimiento alcista si se rompe la resistencia en $67,500. Los niveles de soporte clave se encuentran en $63,200 y $61,800.

Recomendación: Acumular en retrocesos hacia la zona de soporte, con stop loss por debajo de $61,000.`;
      } else if (crypto.symbol === 'ETH') {
        sentiment = 'Muy Alcista';
        recommendation = 'Comprar';
        confidence = 85;
        analysisText = `El análisis técnico de Ethereum (ETH) en timeframe ${tf} muestra señales muy alcistas. 
        
Los indicadores técnicos son extremadamente positivos, con un RSI (72) que indica fuerte impulso alcista sin llegar a niveles de sobrecompra extremos. El MACD muestra un cruce alcista reciente con divergencia positiva.

El precio ha roto una resistencia clave en $3,400 con volumen creciente, lo que valida la ruptura. Se observa un patrón de bandera alcista completado, proyectando un objetivo en $3,800.

Los niveles de soporte se encuentran en $3,400 (anterior resistencia convertida en soporte) y $3,250. La estructura de mercado de máximos y mínimos crecientes confirma la tendencia alcista.

Recomendación: Comprar en los niveles actuales con stop loss por debajo de $3,200.`;
      } else {
        sentiment = 'Neutral';
        recommendation = 'Mantener';
        confidence = 50;
        analysisText = `El análisis técnico de ${crypto.name} (${crypto.symbol}) en timeframe ${tf} muestra señales mixtas. 
        
Los indicadores técnicos no muestran una dirección clara, con un RSI (52) en zona neutral y el MACD cerca de la línea cero. El precio se encuentra en un rango lateral entre soporte y resistencia.

No se observan patrones claros de continuación o reversión en este momento. El volumen ha disminuido, lo que sugiere indecisión en el mercado.

Los niveles de soporte se encuentran en $${(crypto.price * 0.95).toFixed(2)} y $${(crypto.price * 0.9).toFixed(2)}, mientras que las resistencias están en $${(crypto.price * 1.05).toFixed(2)} y $${(crypto.price * 1.1).toFixed(2)}.

Recomendación: Mantener posiciones existentes y esperar una ruptura clara del rango actual antes de tomar nuevas decisiones.`;
      }
      
      // Generar estrategias recomendadas simuladas
      const strategies = [
        { strategy_id: 1, score: Math.floor(Math.random() * 100) },
        { strategy_id: 3, score: Math.floor(Math.random() * 100) },
        { strategy_id: 5, score: Math.floor(Math.random() * 100) }
      ];
      
      // Ordenar estrategias por score
      strategies.sort((a, b) => b.score - a.score);
      
      // Generar niveles de soporte y resistencia
      const supportLevels = [
        crypto.price * 0.95,
        crypto.price * 0.9,
        crypto.price * 0.85
      ].map(p => p.toFixed(crypto.price < 1 ? 8 : 2));
      
      const resistanceLevels = [
        crypto.price * 1.05,
        crypto.price * 1.1,
        crypto.price * 1.15
      ].map(p => p.toFixed(crypto.price < 1 ? 8 : 2));
      
      // Buscar patrones en el texto
      const patterns = [];
      const patternKeywords = ['doble suelo', 'hombro-cabeza-hombro', 'triángulo', 'bandera', 'cuña', 'doble techo', 'canal'];
      
      patternKeywords.forEach(pattern => {
        if (analysisText.toLowerCase().includes(pattern)) {
          patterns.push(pattern.charAt(0).toUpperCase() + pattern.slice(1));
        }
      });
      
      // Crear objeto de análisis
      setAnalysis({
        crypto,
        timeframe: tf,
        sentiment,
        recommendation,
        confidence,
        supportLevels,
        resistanceLevels,
        indicators: {
          rsi: crypto.symbol === 'BTC' ? 58 : crypto.symbol === 'ETH' ? 72 : 52,
          macd: crypto.symbol === 'BTC' || crypto.symbol === 'ETH' ? 'Positivo' : 'Neutral',
          ema20: crypto.price * (1 + (Math.random() * 0.05 - 0.025)),
          ema50: crypto.price * (1 + (Math.random() * 0.1 - 0.05)),
          ema200: crypto.price * (1 + (Math.random() * 0.15 - 0.075))
        },
        patterns,
        priceTargets: {
          short: crypto.price * (1 + (Math.random() * 0.1)),
          medium: crypto.price * (1 + (Math.random() * 0.2)),
          long: crypto.price * (1 + (Math.random() * 0.3))
        },
        risks: [
          'Volatilidad del mercado general',
          'Cambios regulatorios',
          'Correlación con mercados tradicionales'
        ],
        timestamp: new Date().toISOString(),
        rawAnalysis: analysisText,
        strategies
      });
      
    } catch (err) {
      console.error("Error generating analysis:", err);
      setError("No se pudo generar el análisis. Por favor, inténtelo de nuevo más tarde.");
    } finally {
      setLoading(false);
    }
  };

  // Generar análisis cuando se selecciona una criptomoneda y timeframe
  useEffect(() => {
    if (selectedCrypto && timeframe) {
      fetchAnalysis(selectedCrypto, timeframe);
    }
  }, [selectedCrypto, timeframe]);

  // Función para formatear números grandes
  const formatNumber = (num) => {
    if (num >= 1000000000) {
      return `$${(num / 1000000000).toFixed(1)}B`;
    } else if (num >= 1000000) {
      return `$${(num / 1000000).toFixed(1)}M`;
    } else {
      return `$${num.toLocaleString()}`;
    }
  };

  // Función para formatear precios
  const formatPrice = (price) => {
    if (price < 0.01) {
      return `$${price.toFixed(8)}`;
    } else if (price < 1) {
      return `$${price.toFixed(4)}`;
    } else {
      return `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }
  };

  // Función para obtener color según el sentimiento
  const getSentimentColor = (sentiment) => {
    switch (sentiment) {
      case 'Muy Alcista': return 'text-green-500';
      case 'Alcista': return 'text-green-400';
      case 'Neutral': return 'text-yellow-400';
      case 'Bajista': return 'text-red-400';
      case 'Muy Bajista': return 'text-red-500';
      default: return 'text-gray-400';
    }
  };

  return (
    <div className="min-h-screen bg-elegant">
      <div className="container mx-auto px-4 py-8 overflow-y-auto max-h-screen">
        <h1 className="text-4xl font-bold mb-6">Análisis de Mercado</h1>
        
        {/* Tabs */}
        <div className="flex justify-center mb-8">
          <div className="inline-flex bg-gray-800/50 rounded-full p-1">
            <button 
              onClick={() => setActiveTab('market')}
              className={`px-6 py-2 rounded-full transition-colors ${
                activeTab === 'market' ? 'bg-blue-600 text-white' : 'text-gray-300 hover:text-white'
              }`}
            >
              Mercado
            </button>
            <button 
              onClick={() => setActiveTab('technical')}
              className={`px-6 py-2 rounded-full transition-colors ${
                activeTab === 'technical' ? 'bg-blue-600 text-white' : 'text-gray-300 hover:text-white'
              }`}
            >
              Análisis Técnico
            </button>
            <button 
              onClick={() => setActiveTab('sentiment')}
              className={`px-6 py-2 rounded-full transition-colors ${
                activeTab === 'sentiment' ? 'bg-blue-600 text-white' : 'text-gray-300 hover:text-white'
              }`}
            >
              Sentimiento
            </button>
          </div>
        </div>
        
        {/* Contenido de la pestaña */}
        <div className={`grid ${activeTab === 'technical' ? 'md:grid-cols-1' : 'md:grid-cols-3'} gap-6`}>
          {/* Lista de criptomonedas */}
          <div className="md:col-span-1">
            <div className="bg-gray-800/60 p-4 rounded-lg shadow-lg mb-6">
              <h2 className="text-xl font-bold mb-4">Criptomonedas</h2>
              <div className="space-y-3">
                {cryptoData.map(crypto => (
                  <div 
                    key={crypto.id}
                    className={`p-3 rounded-lg cursor-pointer transition-colors ${
                      selectedCrypto && selectedCrypto.id === crypto.id 
                        ? 'bg-blue-900/50 border border-blue-500/50' 
                        : 'bg-gray-900/50 border border-gray-800 hover:bg-gray-800/50'
                    }`}
                    onClick={() => setSelectedCrypto(crypto)}
                  >
                    <div className="flex justify-between items-center">
                      <div className="flex items-center">
                        <div className="w-8 h-8 bg-gray-700 rounded-full flex items-center justify-center mr-3">
                          <span className="font-bold text-sm">{crypto.symbol.charAt(0)}</span>
                        </div>
                        <div>
                          <h3 className="font-medium">{crypto.name}</h3>
                          <span className="text-sm text-gray-400">{crypto.symbol}</span>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-medium">{formatPrice(crypto.price)}</div>
                        <div className={`text-sm ${crypto.change24h >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                          {crypto.change24h >= 0 ? '+' : ''}{crypto.change24h}%
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
          
          {/* Panel de análisis */}
          <div className={`${activeTab === 'technical' ? 'md:col-span-1' : 'md:col-span-2'}`}>
            {!selectedCrypto ? (
              <div className="bg-gray-800/60 p-6 rounded-lg shadow-lg flex flex-col items-center justify-center h-full text-center">
                <div className="mb-4 text-gray-400">
                  <svg className="w-16 h-16 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
                  </svg>
                </div>
                <h3 className="text-xl font-bold mb-2">Selecciona una Criptomoneda</h3>
                <p className="text-gray-400 mb-6 max-w-md">
                  Elige una criptomoneda de la lista para ver análisis detallado, indicadores técnicos y predicciones basadas en IA.
                </p>
              </div>
            ) : (
              <div>
                {/* Encabezado de la criptomoneda */}
                <div className="bg-gray-800/60 p-6 rounded-lg shadow-lg mb-6">
                  <div className="flex justify-between items-start">
                    <div className="flex items-center">
                      <div className="w-12 h-12 bg-gray-700 rounded-full flex items-center justify-center mr-4">
                        <span className="font-bold text-lg">{selectedCrypto.symbol.charAt(0)}</span>
                      </div>
                      <div>
                        <h2 className="text-2xl font-bold">{selectedCrypto.name}</h2>
                        <div className="flex items-center">
                          <span className="text-gray-400 mr-2">{selectedCrypto.symbol}</span>
                          <span className={`px-2 py-0.5 text-xs rounded-full ${
                            selectedCrypto.riskLevel === 'low' ? 'bg-green-900/50 text-green-400' :
                            selectedCrypto.riskLevel === 'medium' ? 'bg-yellow-900/50 text-yellow-400' :
                            selectedCrypto.riskLevel === 'high' ? 'bg-orange-900/50 text-orange-400' :
                            'bg-red-900/50 text-red-400'
                          }`}>
                            {selectedCrypto.riskLevel === 'low' ? 'Riesgo Bajo' :
                             selectedCrypto.riskLevel === 'medium' ? 'Riesgo Medio' :
                             selectedCrypto.riskLevel === 'high' ? 'Riesgo Alto' :
                             'Riesgo Muy Alto'}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold">{formatPrice(selectedCrypto.price)}</div>
                      <div className={`text-lg ${selectedCrypto.change24h >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                        {selectedCrypto.change24h >= 0 ? '+' : ''}{selectedCrypto.change24h}%
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Selector de timeframe */}
                <div className="bg-gray-800/60 p-4 rounded-lg shadow-lg mb-6">
                  <div className="flex justify-between items-center">
                    <h3 className="font-bold">Timeframe</h3>
                    <div className="flex space-x-2">
                      <button 
                        onClick={() => setTimeframe('1h')}
                        className={`px-3 py-1 text-sm rounded-md transition-colors ${
                          timeframe === '1h' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                        }`}
                      >
                        1H
                      </button>
                      <button 
                        onClick={() => setTimeframe('4h')}
                        className={`px-3 py-1 text-sm rounded-md transition-colors ${
                          timeframe === '4h' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                        }`}
                      >
                        4H
                      </button>
                      <button 
                        onClick={() => setTimeframe('1d')}
                        className={`px-3 py-1 text-sm rounded-md transition-colors ${
                          timeframe === '1d' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                        }`}
                      >
                        1D
                      </button>
                      <button 
                        onClick={() => setTimeframe('1w')}
                        className={`px-3 py-1 text-sm rounded-md transition-colors ${
                          timeframe === '1w' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                        }`}
                      >
                        1W
                      </button>
                      <button 
                        onClick={() => setTimeframe('1m')}
                        className={`px-3 py-1 text-sm rounded-md transition-colors ${
                          timeframe === '1m' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                        }`}
                      >
                        1M
                      </button>
                    </div>
                  </div>
                </div>
                
                {/* Contenido del análisis */}
                {activeTab === 'technical' && selectedCrypto ? (
                  // Contenido de la pestaña de análisis técnico
                  <TechnicalCharts symbol={selectedCrypto.symbol} timeframe={timeframe} />
                ) : activeTab === 'technical' ? (
                  // Mensaje para seleccionar criptomoneda en análisis técnico
                  <div className="bg-gray-800/60 p-6 rounded-lg shadow-lg flex flex-col items-center justify-center h-64">
                    <div className="mb-4 text-gray-400">
                      <svg className="w-16 h-16 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                      </svg>
                    </div>
                    <h3 className="text-xl font-bold mb-2">Selecciona una Criptomoneda</h3>
                    <p className="text-gray-400 mb-6 max-w-md text-center">
                      Elige una criptomoneda de la lista para ver gráficos técnicos con indicadores MACD y RSI.
                    </p>
                  </div>
                ) : loading ? (
                  // Indicador de carga
                  <div className="bg-gray-800/60 p-6 rounded-lg shadow-lg flex flex-col items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500 mb-4"></div>
                    <p className="text-gray-400">Analizando {selectedCrypto.name} en timeframe {timeframe}...</p>
                  </div>
                ) : error ? (
                  // Mensaje de error
                  <div className="bg-red-900/30 p-6 rounded-lg shadow-lg mb-6">
                    <h3 className="text-xl font-bold mb-4 text-red-400">Error</h3>
                    <p className="text-white">{error}</p>
                    <button 
                      onClick={() => fetchAnalysis(selectedCrypto, timeframe)}
                      className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 rounded-md text-white"
                    >
                      Reintentar
                    </button>
                  </div>
                ) : analysis ? (
                  // Resultados del análisis
                  <div className="bg-gray-800/60 p-6 rounded-lg shadow-lg mb-6">
                    <h3 className="text-xl font-bold mb-4">Análisis de {analysis.crypto.name}</h3>
                    <p className="mb-4">Timeframe: {analysis.timeframe}</p>
                    
                    <div className="grid grid-cols-2 gap-4 mb-6">
                      <div>
                        <h4 className="font-bold mb-2">Sentimiento</h4>
                        <p className={getSentimentColor(analysis.sentiment)}>{analysis.sentiment}</p>
                      </div>
                      <div>
                        <h4 className="font-bold mb-2">Recomendación</h4>
                        <p>{analysis.recommendation} ({analysis.confidence}% confianza)</p>
                      </div>
                    </div>
                    
                    {analysis.rawAnalysis && (
                      <div className="mt-4 p-4 bg-gray-900/50 rounded-lg">
                        <h4 className="font-bold mb-2">Análisis Detallado</h4>
                        <p className="text-sm whitespace-pre-line">{analysis.rawAnalysis}</p>
                      </div>
                    )}
                    
                    {analysis.strategies && analysis.strategies.length > 0 && (
                      <div className="mt-6">
                        <h4 className="font-bold mb-2">Estrategias Recomendadas</h4>
                        <div className="grid grid-cols-2 gap-2">
                          {analysis.strategies.map((strategy, index) => (
                            <div key={index} className="bg-gray-900/50 p-3 rounded-lg">
                              <p className="text-sm">Estrategia #{strategy.strategy_id}</p>
                              {strategy.score !== null && (
                                <p className="text-xs text-gray-400">Score: {strategy.score}</p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : null}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
