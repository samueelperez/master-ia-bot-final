"use client";

import { usePathname } from 'next/navigation';
import Navbar from './Navbar';

export default function NavbarWrapper() {
  const pathname = usePathname();
  
  if (pathname === '/') {
    return null;
  }
  
  return (
    <>
      <Navbar />
      <style jsx global>{`
        main {
          padding-top: 4rem;
        }
      `}</style>
    </>
  );
} 