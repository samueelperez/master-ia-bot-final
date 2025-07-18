"use client";

import { useState, useEffect } from 'react';
import ChatBot from '../components/ChatBot';

export default function DashboardPage() {
  const [userData, setUserData] = useState({
    name: 'Usuario',
    lastLogin: new Date().toLocaleString()
  });

  return (
    <div className="min-h-screen bg-elegant pt-20 pb-10 px-4">
      <div className="container mx-auto max-w-7xl">
        <div className="card p-0 overflow-hidden flex flex-col h-[calc(100vh-120px)]">
          <div className="p-4 border-b border-gray-700 bg-gray-800 flex items-center">
            <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center mr-3">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Asistente CryptoAI</h2>
              <p className="text-gray-400 text-sm">
                Análisis avanzado de mercados de criptomonedas
              </p>
            </div>
          </div>
          
          {/* Componente de ChatBot */}
          <ChatBot />
        </div>
      </div>
    </div>
  );
}
