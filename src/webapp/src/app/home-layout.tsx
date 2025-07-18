import type { ReactNode } from "react";
import Link from "next/link";

export default function HomeLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-black text-white overflow-hidden">
      <header className="border-b border-gray-800/50 backdrop-blur-md bg-black/70 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex justify-between items-center">
            <Link href="/" className="flex items-center space-x-2 group">
              <div className="relative w-10 h-10 flex items-center justify-center">
                <div className="absolute inset-0 bg-blue-600 rounded-lg transform rotate-45 group-hover:rotate-[135deg] transition-transform duration-500"></div>
                <svg 
                  className="h-6 w-6 text-white relative z-10" 
                  fill="none" 
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M13 10V3L4 14h7v7l9-11h-7z" 
                  />
                </svg>
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight">
                  <span className="text-white">Crypto</span>
                  <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">AI Bot</span>
                </h1>
              </div>
            </Link>
            <nav>
              <ul className="flex space-x-8">
                <li>
                  <Link 
                    href="/" 
                    className="font-medium text-gray-300 hover:text-white transition-colors relative group"
                  >
                    Inicio
                    <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-blue-500 group-hover:w-full transition-all duration-300"></span>
                  </Link>
                </li>
                <li>
                  <Link 
                    href="/analysis" 
                    className="font-medium text-gray-300 hover:text-white transition-colors relative group"
                  >
                    Análisis
                    <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-blue-500 group-hover:w-full transition-all duration-300"></span>
                  </Link>
                </li>
                <li>
                  <Link 
                    href="/strategies" 
                    className="font-medium text-gray-300 hover:text-white transition-colors relative group"
                  >
                    Estrategias
                    <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-blue-500 group-hover:w-full transition-all duration-300"></span>
                  </Link>
                </li>
              </ul>
            </nav>
          </div>
        </div>
      </header>
      <main className="container mx-auto px-4 flex-grow overflow-hidden">
        {children}
      </main>
    </div>
  );
}
