"use client";

import { useState, useEffect } from 'react';
import Link from 'next/link';
import MouseTrailWrapper from './components/MouseTrailWrapper';

export default function HomePage() {
  const [cryptoData, setCryptoData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchCryptoData = async () => {
    try {
      const response = await fetch(
        'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=bitcoin,ethereum,solana,cardano,polkadot&order=market_cap_desc&per_page=5&page=1&sparkline=false&price_change_percentage=24h'
      );
      
      if (!response.ok) {
        throw new Error('Error al obtener datos de criptomonedas');
      }

      const data = await response.json();
      setCryptoData(data.map(coin => ({
        name: coin.name,
        symbol: coin.symbol.toUpperCase(),
        price: coin.current_price,
        change24h: coin.price_change_percentage_24h
      })));
      setError(null);
    } catch (err) {
      setError('Error al cargar los datos de criptomonedas');
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCryptoData();
    const interval = setInterval(fetchCryptoData, 30000); // Actualizar cada 30 segundos
    
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-screen overflow-hidden bg-elegant">
      <MouseTrailWrapper />
      {/* Hero Section */}
      <section className="h-screen flex flex-col justify-between relative overflow-hidden">
        <div className="absolute inset-0 z-0">
          <div className="absolute inset-0 bg-gradient-to-b from-blue-900/20 to-black/80"></div>
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_30%,rgba(59,130,246,0.2),transparent_40%)]"></div>
        </div>
        
        <div className="container mx-auto relative z-10 pt-32">
          <div className="max-w-3xl">
            <h1 className="text-5xl md:text-6xl font-bold mb-6">
              Trading de Criptomonedas con <span className="gradient-text">Inteligencia Artificial</span>
            </h1>
            <p className="text-xl md:text-2xl text-gray-300 mb-8">
              Potencia tus decisiones de inversión con análisis avanzado de IA y estrategias optimizadas para el mercado de criptomonedas.
            </p>
            <div className="flex flex-wrap gap-4">
              <Link 
                href="/analysis" 
                className="btn btn-primary text-lg px-8 py-4 rounded-full transform transition-all hover:scale-105 hover:shadow-lg hover:shadow-blue-500/20"
              >
                Analizar Mercado
              </Link>
            </div>
          </div>
        </div>
        {/* Crypto Ticker dentro del hero, pegado abajo */}
        <div className="relative z-10">
          <div className="py-6 bg-gray-900/50">
            <div className="container mx-auto">
              <div className="flex overflow-x-auto scrollbar-hide">
                {loading ? (
                  <div className="flex items-center justify-center w-full">
                    <div className="animate-spin rounded-full h-6 w-6 border-t-2 border-b-2 border-blue-500"></div>
                  </div>
                ) : error ? (
                  <div className="text-red-500 text-center w-full">{error}</div>
                ) : (
                  <div className="flex animate-marquee whitespace-nowrap">
                    {[...cryptoData, ...cryptoData].map((crypto, index) => (
                      <div key={index} className="flex items-center mx-6">
                        <span className="font-bold mr-2">{crypto.symbol}</span>
                        <span className="mr-2">${crypto.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                        <span className={`${crypto.change24h >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                          {crypto.change24h >= 0 ? '+' : ''}{crypto.change24h.toFixed(2)}%
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
