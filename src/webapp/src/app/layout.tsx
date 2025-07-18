import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import NavbarWrapper from "./components/NavbarWrapper";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "CryptoAI - Trading con Inteligencia Artificial",
  description: "Análisis avanzado de criptomonedas y estrategias de trading optimizadas con inteligencia artificial",
  keywords: "criptomonedas, trading, inteligencia artificial, análisis técnico, estrategias, bitcoin, ethereum",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body className={inter.className + ' overflow-hidden'}>
        <div className="min-h-screen bg-black text-white">
          <NavbarWrapper />
          <main>
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
