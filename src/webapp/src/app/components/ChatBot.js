"use client";

import { useState, useRef, useEffect } from 'react';
import { generateAnalysis, getAvailableSymbols } from '../../lib/api';

export default function ChatBot() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: 'assistant',
      content: 'Bienvenido al Asistente de Análisis de CryptoAI. Estoy aquí para proporcionarle información precisa y análisis detallados sobre el mercado de criptomonedas. Puede preguntarme sobre análisis técnico de cualquier criptomoneda (por ejemplo: "Analiza BTC en timeframe diario" o "¿Qué opinas de Ethereum en 4h?").',
      timestamp: new Date()
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [availableSymbols, setAvailableSymbols] = useState(['BTC', 'ETH', 'SOL', 'DOGE', 'SHIB', 'XRP', 'ADA', 'AVAX', 'DOT', 'MATIC']);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  
  // Cargar símbolos disponibles
  useEffect(() => {
    const loadSymbols = async () => {
      try {
        const symbols = await getAvailableSymbols();
        setAvailableSymbols(symbols);
      } catch (err) {
        console.error("Error loading symbols:", err);
      }
    };
    
    loadSymbols();
  }, []);

  // Función para detectar el símbolo de criptomoneda en el mensaje del usuario
  const detectCryptoSymbol = (message) => {
    const lowerCaseMessage = message.toLowerCase();
    
    // Mapeo de nombres comunes a símbolos
    const cryptoNameToSymbol = {
      'bitcoin': 'BTC',
      'ethereum': 'ETH',
      'solana': 'SOL',
      'dogecoin': 'DOGE',
      'shiba': 'SHIB',
      'ripple': 'XRP',
      'cardano': 'ADA',
      'avalanche': 'AVAX',
      'polkadot': 'DOT',
      'polygon': 'MATIC'
    };
    
    // Buscar símbolos directamente en el mensaje
    for (const symbol of availableSymbols) {
      const symbolRegex = new RegExp(`\\b${symbol}\\b`, 'i');
      if (symbolRegex.test(message)) {
        return symbol;
      }
    }
    
    // Buscar nombres de criptomonedas en el mensaje
    for (const [name, symbol] of Object.entries(cryptoNameToSymbol)) {
      if (lowerCaseMessage.includes(name)) {
        return symbol;
      }
    }
    
    return null;
  };
  
  // Función para detectar el timeframe en el mensaje del usuario
  const detectTimeframe = (message) => {
    const lowerCaseMessage = message.toLowerCase();
    const timeframes = {
      'minuto': '1m',
      'minutos': '1m',
      '1m': '1m',
      '5m': '5m',
      '15m': '15m',
      '30m': '30m',
      'hora': '1h',
      'horario': '1h',
      '1h': '1h',
      '4h': '4h',
      'diario': '1d',
      'día': '1d',
      'dias': '1d',
      'diario': '1d',
      '1d': '1d',
      'semanal': '1w',
      'semana': '1w',
      '1w': '1w',
      'mensual': '1M',
      'mes': '1M',
      '1M': '1M'
    };
    
    for (const [key, value] of Object.entries(timeframes)) {
      if (lowerCaseMessage.includes(key)) {
        return value;
      }
    }
    
    // Timeframe por defecto si no se especifica
    return '1d';
  };
  
  // Función para obtener la respuesta del asistente
  const getAIResponse = async (userMessage) => {
    setIsLoading(true);
    
    try {
      const lowerCaseMessage = userMessage.toLowerCase();
      
      // Detectar si el usuario está pidiendo un análisis
      const isAnalysisRequest = 
        lowerCaseMessage.includes('analiza') || 
        lowerCaseMessage.includes('análisis') || 
        lowerCaseMessage.includes('qué opinas') || 
        lowerCaseMessage.includes('que opinas') ||
        lowerCaseMessage.includes('cómo ves') ||
        lowerCaseMessage.includes('como ves');
      
      // Detectar el símbolo de la criptomoneda
      const cryptoSymbol = detectCryptoSymbol(userMessage);
      
      // Si es una solicitud de análisis y se detectó un símbolo, generar análisis
      if (isAnalysisRequest && cryptoSymbol) {
        const timeframe = detectTimeframe(userMessage);
        
        try {
          // Llamar a la API para obtener el análisis
          console.log(`Solicitando análisis para ${cryptoSymbol} en timeframe ${timeframe}`);
          const analysisResult = await generateAnalysis({
            symbol: cryptoSymbol,
            timeframes: [timeframe],
            user_prompt: userMessage
          });
          
          setIsLoading(false);
          return analysisResult.analysis;
        } catch (error) {
          console.error("Error calling API:", error);
          
          // Respuesta de fallback en caso de error
          setIsLoading(false);
          return `Lo siento, no he podido obtener el análisis para ${cryptoSymbol} en este momento. El servicio de análisis parece no estar disponible. Por favor, inténtelo de nuevo más tarde o contacte con el administrador del sistema.`;
        }
      } else {
        // Respuestas predefinidas para otros tipos de mensajes
        let response = "Entiendo su consulta, pero necesitaría información más específica para proporcionarle un análisis adecuado. ¿Podría detallar más su pregunta sobre el mercado de criptomonedas? Por ejemplo, puede preguntarme 'Analiza BTC en timeframe diario'.";
        
        if (cryptoSymbol) {
          response = `${cryptoSymbol} es un activo digital importante en el mercado de criptomonedas. Para obtener un análisis detallado, puede preguntarme específicamente por un análisis técnico, por ejemplo: "Analiza ${cryptoSymbol} en timeframe diario" o "¿Qué opinas de ${cryptoSymbol} en 4h?"`;
        } else if (lowerCaseMessage.includes('hola') || lowerCaseMessage.includes('buenos días') || lowerCaseMessage.includes('buenas')) {
          response = "Saludos. Soy el Asistente de Análisis de CryptoAI, especializado en proporcionar información precisa y análisis detallados sobre el mercado de criptomonedas. Estoy a su disposición para resolver consultas sobre análisis técnico, fundamentales de proyectos blockchain, estrategias de inversión y tendencias de mercado. ¿En qué puedo asistirle hoy?";
        } else if (lowerCaseMessage.includes('gracias')) {
          response = "Agradezco su consulta. Estoy a su disposición para cualquier análisis adicional o aclaración que pueda requerir sobre el mercado de criptoactivos. No dude en contactarme para futuras consultas.";
        } else if (lowerCaseMessage.includes('invertir') || lowerCaseMessage.includes('inversión')) {
          response = "La inversión en activos digitales requiere un enfoque estratégico y gestión de riesgos adecuada. Recomendamos: 1) Establecer una tesis de inversión clara basada en horizontes temporales definidos. 2) Implementar diversificación entre diferentes clases de criptoactivos. 3) Utilizar gestión de posiciones con stop-loss y take-profit. 4) Mantener un porcentaje significativo en activos de mayor capitalización para reducir la volatilidad de la cartera. 5) Considerar estrategias de DCA (Dollar-Cost Averaging) para mitigar el riesgo de entrada. ¿Desea información sobre alguna estrategia específica?";
        }
        
        setIsLoading(false);
        return response;
      }
    } catch (error) {
      console.error("Error in getAIResponse:", error);
      setIsLoading(false);
      return "Lo siento, ha ocurrido un error al procesar su solicitud. Por favor, inténtelo de nuevo más tarde.";
    }
  };

  // Manejar el envío de mensajes
  const handleSendMessage = async (e) => {
    e.preventDefault();
    
    if (!inputValue.trim()) return;
    
    // Añadir mensaje del usuario
    const userMessage = {
      id: messages.length + 1,
      role: 'user',
      content: inputValue,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    
    // Obtener respuesta del asistente
    const aiResponse = await getAIResponse(inputValue);
    
    // Añadir respuesta del asistente
    const assistantMessage = {
      id: messages.length + 2,
      role: 'assistant',
      content: aiResponse,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, assistantMessage]);
  };

  // Hacer scroll automático al último mensaje
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Enfocar el input al cargar
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Formatear la hora
  const formatTime = (date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="flex flex-col h-full bg-gray-900">
      {/* Área de mensajes */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-900">
        {messages.map((message) => (
          <div 
            key={message.id} 
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div 
              className={`max-w-[80%] rounded-lg p-4 ${
                message.role === 'user' 
                  ? 'bg-primary text-white rounded-tr-none shadow-lg' 
                  : 'bg-gray-800 text-white rounded-tl-none shadow-lg border border-gray-700'
              }`}
            >
              {message.role === 'assistant' && (
                <div className="flex items-center mb-2">
                  <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center mr-2">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-white" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span className="text-xs font-semibold text-primary">Asistente CryptoAI</span>
                </div>
              )}
              <div className="text-sm leading-relaxed">{message.content}</div>
              <div className="text-xs text-gray-400 mt-2 text-right">
                {formatTime(message.timestamp)}
              </div>
            </div>
          </div>
        ))}
        
        {/* Indicador de "escribiendo..." */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 text-white rounded-lg rounded-tl-none p-3 border border-gray-700">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      {/* Área de entrada de texto */}
      <div className="border-t border-gray-700 p-4 bg-gray-800">
        <form onSubmit={handleSendMessage} className="flex space-x-2 mb-4">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Formule su consulta sobre el mercado de criptomonedas..."
            className="flex-1 input focus:ring-2 focus:ring-primary bg-gray-700 border border-gray-600 py-3 px-4 text-sm text-white"
            disabled={isLoading}
          />
          <button
            type="submit"
            className="btn btn-primary px-4 flex items-center justify-center"
            disabled={isLoading || !inputValue.trim()}
          >
            {isLoading ? (
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
              </svg>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
