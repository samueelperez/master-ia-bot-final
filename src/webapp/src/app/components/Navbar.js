"use client";

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function Navbar() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 10) {
        setScrolled(true);
      } else {
        setScrolled(false);
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const isActive = (path) => {
    return pathname === path;
  };

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
      scrolled ? 'bg-black/80 backdrop-blur-md shadow-lg' : 'bg-transparent'
    }`}>
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center">
            <span className="text-xl font-bold gradient-text">CryptoAI</span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-8">
            <Link 
              href="/" 
              className={`nav-link ${isActive('/') ? 'text-blue-400' : 'text-gray-300 hover:text-white'}`}
            >
              Inicio
            </Link>
            <Link 
              href="/analysis" 
              className={`nav-link ${isActive('/analysis') ? 'text-blue-400' : 'text-gray-300 hover:text-white'}`}
            >
              Análisis
            </Link>
            <Link 
              href="/strategies" 
              className={`nav-link ${isActive('/strategies') ? 'text-blue-400' : 'text-gray-300 hover:text-white'}`}
            >
              Estrategias
            </Link>
            <Link 
              href="/portfolio" 
              className={`nav-link ${isActive('/portfolio') ? 'text-blue-400' : 'text-gray-300 hover:text-white'}`}
            >
              Portfolio
            </Link>
            <Link 
              href="/dashboard" 
              className="btn btn-sm btn-primary"
            >
              Dashboard
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <div className="md:hidden">
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="text-gray-300 hover:text-white focus:outline-none"
            >
              {isMenuOpen ? (
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {isMenuOpen && (
        <div className="md:hidden bg-gray-900/95 backdrop-blur-md">
          <div className="container mx-auto px-4 py-4 space-y-4">
            <Link 
              href="/" 
              className={`block py-2 ${isActive('/') ? 'text-blue-400' : 'text-gray-300 hover:text-white'}`}
              onClick={() => setIsMenuOpen(false)}
            >
              Inicio
            </Link>
            <Link 
              href="/analysis" 
              className={`block py-2 ${isActive('/analysis') ? 'text-blue-400' : 'text-gray-300 hover:text-white'}`}
              onClick={() => setIsMenuOpen(false)}
            >
              Análisis
            </Link>
            <Link 
              href="/strategies" 
              className={`block py-2 ${isActive('/strategies') ? 'text-blue-400' : 'text-gray-300 hover:text-white'}`}
              onClick={() => setIsMenuOpen(false)}
            >
              Estrategias
            </Link>
            <Link 
              href="/portfolio" 
              className={`block py-2 ${isActive('/portfolio') ? 'text-blue-400' : 'text-gray-300 hover:text-white'}`}
              onClick={() => setIsMenuOpen(false)}
            >
              Portfolio
            </Link>
            <Link 
              href="/dashboard" 
              className="block py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
              onClick={() => setIsMenuOpen(false)}
            >
              Dashboard
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}
