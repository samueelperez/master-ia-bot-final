"use client";

import { useState } from 'react';
import Link from 'next/link';

export default function StrategiesPage() {
  const [selectedStrategy, setSelectedStrategy] = useState(null);
  const [riskLevel, setRiskLevel] = useState('medium');

  // Datos de ejemplo para las estrategias
  const strategies = [
    {
      id: 1,
      name: "Scalping de Memecoins",
      description: "Estrategia de trading a corto plazo que aprovecha la alta volatilidad de las memecoins para obtener beneficios rápidos.",
      riskLevel: "high",
      timeframe: "Corto plazo (minutos a horas)",
      profitPotential: "Alto",
      requirements: "Monitoreo constante, reacción rápida, capital disponible para entradas múltiples",
      steps: [
        "Identificar memecoins con volumen creciente y momentum positivo",
        "Entrar en posición cuando se confirme un patrón de ruptura",
        "Establecer take profit en 5-15% y stop loss en 2-3%",
        "Salir de la posición cuando se alcance el objetivo o se active el stop loss",
        "Nunca mantener posiciones abiertas por más de 24 horas"
      ],
      performance: {
        winRate: "62%",
        avgProfit: "8.5%",
        avgLoss: "2.8%",
        maxDrawdown: "18%"
      }
    },
    {
      id: 2,
      name: "Holding de Largo Plazo",
      description: "Estrategia de inversión que consiste en comprar y mantener criptomonedas de alta capitalización durante períodos prolongados.",
      riskLevel: "medium",
      timeframe: "Largo plazo (meses a años)",
      profitPotential: "Medio-Alto",
      requirements: "Paciencia, capital que no se necesite a corto plazo, análisis fundamental",
      steps: [
        "Seleccionar criptomonedas con fundamentales sólidos y casos de uso reales",
        "Comprar en momentos de corrección del mercado o mediante DCA (Dollar Cost Averaging)",
        "Mantener durante al menos un ciclo de mercado completo (3-4 años)",
        "Rebalancear la cartera cada 6 meses",
        "Establecer niveles de salida basados en valoraciones históricas"
      ],
      performance: {
        winRate: "85%",
        avgProfit: "320%",
        avgLoss: "25%",
        maxDrawdown: "65%"
      }
    },
    {
      id: 3,
      name: "Swing Trading con Altcoins",
      description: "Estrategia que busca capturar movimientos de precio en altcoins durante períodos de días a semanas.",
      riskLevel: "medium",
      timeframe: "Medio plazo (días a semanas)",
      profitPotential: "Medio",
      requirements: "Análisis técnico, seguimiento de tendencias, gestión de riesgos",
      steps: [
        "Identificar altcoins en tendencia alcista con volumen creciente",
        "Entrar en soportes técnicos o retrocesos de Fibonacci",
        "Establecer take profit en resistencias clave y stop loss bajo soportes importantes",
        "Utilizar trailing stops para maximizar ganancias en tendencias fuertes",
        "Salir completamente cuando se observen señales de agotamiento"
      ],
      performance: {
        winRate: "58%",
        avgProfit: "42%",
        avgLoss: "12%",
        maxDrawdown: "28%"
      }
    },
    {
      id: 4,
      name: "Range Trading",
      description: "Estrategia que aprovecha los movimientos laterales del mercado, comprando en soporte y vendiendo en resistencia.",
      riskLevel: "low",
      timeframe: "Corto a medio plazo (días)",
      profitPotential: "Bajo-Medio",
      requirements: "Identificación precisa de rangos, paciencia, disciplina",
      steps: [
        "Identificar criptomonedas que se mueven en un rango definido",
        "Comprar cerca del soporte del rango con volumen confirmatorio",
        "Vender cerca de la resistencia del rango",
        "Establecer stop loss justo por debajo del soporte",
        "Repetir el proceso mientras el rango se mantenga intacto"
      ],
      performance: {
        winRate: "72%",
        avgProfit: "12%",
        avgLoss: "5%",
        maxDrawdown: "15%"
      }
    },
    {
      id: 5,
      name: "Breakout Trading",
      description: "Estrategia que busca capitalizar las rupturas de patrones técnicos o niveles de precio significativos.",
      riskLevel: "high",
      timeframe: "Corto plazo (horas a días)",
      profitPotential: "Alto",
      requirements: "Identificación de patrones, reacción rápida, gestión de riesgos estricta",
      steps: [
        "Identificar criptomonedas formando patrones de consolidación (triángulos, banderas, etc.)",
        "Establecer alertas en niveles clave de ruptura",
        "Entrar cuando el precio rompa con volumen significativo",
        "Establecer stop loss en el lado opuesto del patrón",
        "Tomar beneficios en objetivos técnicos o cuando el impulso disminuya"
      ],
      performance: {
        winRate: "55%",
        avgProfit: "35%",
        avgLoss: "12%",
        maxDrawdown: "22%"
      }
    }
  ];

  // Filtrar estrategias por nivel de riesgo
  const filteredStrategies = riskLevel === 'all' 
    ? strategies 
    : strategies.filter(strategy => strategy.riskLevel === riskLevel);

  return (
    <div className="bg-elegant min-h-screen py-8">
      <div className="container mx-auto px-4">
        <h1 className="text-4xl font-bold mb-6">Estrategias de Trading</h1>
        <p className="text-xl mb-8">
          Explora diferentes estrategias de trading para criptomonedas según tu perfil de riesgo
        </p>
        
        {/* Filtro de nivel de riesgo */}
        <div className="mb-8">
          <h2 className="text-xl font-bold mb-4">Filtrar por nivel de riesgo</h2>
          <div className="flex flex-wrap gap-3">
            <button 
              onClick={() => setRiskLevel('all')}
              className={`px-4 py-2 rounded-full transition-colors ${
                riskLevel === 'all' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              Todos
            </button>
            <button 
              onClick={() => setRiskLevel('low')}
              className={`px-4 py-2 rounded-full transition-colors ${
                riskLevel === 'low' 
                  ? 'bg-green-600 text-white' 
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              Riesgo Bajo
            </button>
            <button 
              onClick={() => setRiskLevel('medium')}
              className={`px-4 py-2 rounded-full transition-colors ${
                riskLevel === 'medium' 
                  ? 'bg-yellow-600 text-white' 
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              Riesgo Medio
            </button>
            <button 
              onClick={() => setRiskLevel('high')}
              className={`px-4 py-2 rounded-full transition-colors ${
                riskLevel === 'high' 
                  ? 'bg-red-600 text-white' 
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              Riesgo Alto
            </button>
          </div>
        </div>
        
        {/* Lista de estrategias */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredStrategies.map(strategy => (
            <div 
              key={strategy.id}
              className="crypto-card cursor-pointer transform transition-all hover:scale-105"
              onClick={() => setSelectedStrategy(strategy)}
            >
              <h3 className="text-xl font-bold mb-3">{strategy.name}</h3>
              <div className="flex items-center mb-3">
                <span className={`inline-block w-3 h-3 rounded-full mr-2 ${
                  strategy.riskLevel === 'low' ? 'bg-green-500' :
                  strategy.riskLevel === 'medium' ? 'bg-yellow-500' : 'bg-red-500'
                }`}></span>
                <span className="text-sm">
                  {strategy.riskLevel === 'low' ? 'Riesgo Bajo' :
                   strategy.riskLevel === 'medium' ? 'Riesgo Medio' : 'Riesgo Alto'}
                </span>
              </div>
              <p className="text-gray-300 mb-4 line-clamp-3">{strategy.description}</p>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Timeframe: {strategy.timeframe}</span>
                <span className="text-blue-400">Win Rate: {strategy.performance.winRate}</span>
              </div>
            </div>
          ))}
        </div>
        
        {/* Modal de detalles de estrategia */}
        {selectedStrategy && (
          <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50">
            <div className="bg-gray-900 rounded-lg max-w-3xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6">
                <div className="flex justify-between items-start mb-6">
                  <h2 className="text-2xl font-bold">{selectedStrategy.name}</h2>
                  <button 
                    onClick={() => setSelectedStrategy(null)}
                    className="text-gray-400 hover:text-white"
                  >
                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
                
                <div className="flex items-center mb-4">
                  <span className={`inline-block w-3 h-3 rounded-full mr-2 ${
                    selectedStrategy.riskLevel === 'low' ? 'bg-green-500' :
                    selectedStrategy.riskLevel === 'medium' ? 'bg-yellow-500' : 'bg-red-500'
                  }`}></span>
                  <span>
                    {selectedStrategy.riskLevel === 'low' ? 'Riesgo Bajo' :
                     selectedStrategy.riskLevel === 'medium' ? 'Riesgo Medio' : 'Riesgo Alto'}
                  </span>
                </div>
                
                <p className="text-gray-300 mb-6">{selectedStrategy.description}</p>
                
                <div className="grid md:grid-cols-2 gap-6 mb-6">
                  <div>
                    <h3 className="text-lg font-bold mb-3">Detalles</h3>
                    <ul className="space-y-2 text-gray-300">
                      <li><span className="text-gray-400">Timeframe:</span> {selectedStrategy.timeframe}</li>
                      <li><span className="text-gray-400">Potencial de beneficio:</span> {selectedStrategy.profitPotential}</li>
                      <li><span className="text-gray-400">Requisitos:</span> {selectedStrategy.requirements}</li>
                    </ul>
                  </div>
                  
                  <div>
                    <h3 className="text-lg font-bold mb-3">Rendimiento</h3>
                    <ul className="space-y-2">
                      <li className="flex justify-between">
                        <span className="text-gray-400">Win Rate:</span>
                        <span className="text-blue-400">{selectedStrategy.performance.winRate}</span>
                      </li>
                      <li className="flex justify-between">
                        <span className="text-gray-400">Beneficio promedio:</span>
                        <span className="text-green-400">{selectedStrategy.performance.avgProfit}</span>
                      </li>
                      <li className="flex justify-between">
                        <span className="text-gray-400">Pérdida promedio:</span>
                        <span className="text-red-400">{selectedStrategy.performance.avgLoss}</span>
                      </li>
                      <li className="flex justify-between">
                        <span className="text-gray-400">Drawdown máximo:</span>
                        <span className="text-yellow-400">{selectedStrategy.performance.maxDrawdown}</span>
                      </li>
                    </ul>
                  </div>
                </div>
                
                <div className="mb-6">
                  <h3 className="text-lg font-bold mb-3">Pasos a seguir</h3>
                  <ol className="list-decimal list-inside space-y-2 text-gray-300">
                    {selectedStrategy.steps.map((step, index) => (
                      <li key={index}>{step}</li>
                    ))}
                  </ol>
                </div>
                
                <div className="flex justify-end">
                  <button 
                    className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-6 rounded transition-colors"
                  >
                    Aplicar Estrategia
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {/* Sección de recursos adicionales */}
        <div className="mt-12">
          <h2 className="text-2xl font-bold mb-6">Recursos Adicionales</h2>
          <div className="grid md:grid-cols-3 gap-6">
            <div className="bg-gray-900/80 p-6 rounded-lg border border-gray-800">
              <h3 className="text-xl font-bold mb-3">Gestión de Riesgos</h3>
              <p className="text-gray-300 mb-4">
                Aprende a proteger tu capital con técnicas avanzadas de gestión de riesgos para trading de criptomonedas.
              </p>
              <a href="#" className="text-blue-400 hover:text-blue-300 inline-flex items-center">
                Ver guía completa
                <svg className="w-4 h-4 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
              </a>
            </div>
            
            <div className="bg-gray-900/80 p-6 rounded-lg border border-gray-800">
              <h3 className="text-xl font-bold mb-3">Análisis Técnico</h3>
              <p className="text-gray-300 mb-4">
                Domina los patrones de velas, indicadores y herramientas de análisis técnico específicas para mercados de criptomonedas.
              </p>
              <a href="#" className="text-blue-400 hover:text-blue-300 inline-flex items-center">
                Ver tutoriales
                <svg className="w-4 h-4 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
              </a>
            </div>
            
            <div className="bg-gray-900/80 p-6 rounded-lg border border-gray-800">
              <h3 className="text-xl font-bold mb-3">Psicología del Trading</h3>
              <p className="text-gray-300 mb-4">
                Desarrolla una mentalidad ganadora y aprende a controlar las emociones que afectan tus decisiones de trading.
              </p>
              <a href="#" className="text-blue-400 hover:text-blue-300 inline-flex items-center">
                Ver recursos
                <svg className="w-4 h-4 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
