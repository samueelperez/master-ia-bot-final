"use client";

import { useEffect, useState } from 'react';
import MouseTrail from './MouseTrail';

export default function MouseTrailWrapper() {
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  if (!isClient) {
    return null;
  }

  return <MouseTrail />;
}
