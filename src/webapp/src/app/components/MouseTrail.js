"use client";

import { useEffect, useRef } from 'react';

export default function MouseTrail() {
  const canvasRef = useRef(null);
  const particlesRef = useRef([]);
  const mousePositionRef = useRef({ x: 0, y: 0 });
  const animationFrameRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    
    // Configuración - Colores de nebulosa espacial que coinciden con la nueva paleta
    const colors = [
      'rgba(109, 40, 217, 0.2)',  // Púrpura (--color-primary)
      'rgba(139, 92, 246, 0.2)',  // Púrpura claro (--color-primary-light)
      'rgba(91, 33, 182, 0.2)',   // Púrpura oscuro (--color-primary-dark)
      'rgba(79, 70, 229, 0.2)',   // Índigo (--color-secondary)
      'rgba(236, 72, 153, 0.2)',  // Rosa (--color-accent)
      'rgba(190, 24, 93, 0.2)',   // Rosa oscuro
      'rgba(67, 56, 202, 0.2)'    // Índigo oscuro
    ];
    const maxParticles = 150;        // Menos partículas
    const particleSize = 15;         // Partículas más pequeñas
    const particleLifespan = 150;    // Duración moderada
    
    // Ajustar tamaño del canvas
    function resizeCanvas() {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    }
    
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    
    // Seguimiento del ratón
    function handleMouseMove(e) {
      mousePositionRef.current = { x: e.clientX, y: e.clientY };
      
      // Crear varias partículas para efecto de nebulosa más denso
      for (let i = 0; i < 2; i++) {
        const color = colors[Math.floor(Math.random() * colors.length)];
        const size = particleSize * (0.5 + Math.random() * 0.8); // Tamaño más variable
        
        particlesRef.current.push({
          x: e.clientX + (Math.random() - 0.5) * 15, // Posición más aleatoria
          y: e.clientY + (Math.random() - 0.5) * 15,
          size: size,
          color: color,
          life: particleLifespan + Math.random() * 100, // Vida mucho más variable
          initialLife: particleLifespan + Math.random() * 100,
          velocity: {
            x: (Math.random() - 0.5) * 1.5, // Velocidad más lenta para efecto nebulosa
            y: (Math.random() - 0.5) * 1.5 - 0.2 // Ligera tendencia a subir
          },
          // Añadir rotación para partículas
          rotation: Math.random() * Math.PI * 2,
          rotationSpeed: (Math.random() - 0.5) * 0.02,
          // Añadir pulsación para efecto nebulosa
          pulsate: Math.random() * 0.1,
          pulsateSpeed: 0.01 + Math.random() * 0.02
        });
      }
      
      // Limitar número de partículas
      if (particlesRef.current.length > maxParticles) {
        particlesRef.current = particlesRef.current.slice(particlesRef.current.length - maxParticles);
      }
    }
    
    window.addEventListener('mousemove', handleMouseMove);
    
    // Animación
    function animate() {
      // Limpiar completamente el canvas en cada frame para evitar oscurecimiento
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      // Configurar modo de mezcla para efecto nebulosa
      ctx.globalCompositeOperation = 'screen'; // Mejor para nebulosa espacial
      
      // Actualizar y dibujar partículas
      particlesRef.current = particlesRef.current
        .map(particle => {
          // Actualizar
          particle.x += particle.velocity.x;
          particle.y += particle.velocity.y;
          particle.life -= 0.3; // Reducción aún más lenta de la vida
          particle.rotation += particle.rotationSpeed;
          
          // Efecto de pulsación
          particle.size += Math.sin(particle.pulsateSpeed * Date.now()) * particle.pulsate;
          
          // Calcular opacidad basada en la vida
          const lifeRatio = particle.life / particle.initialLife;
          const opacity = lifeRatio * 0.3; // Máximo 0.3 de opacidad
          
          // Reducir velocidad gradualmente para efecto de disipación
          particle.velocity.x *= 0.995;
          particle.velocity.y *= 0.995;
          
          // Añadir ligero movimiento aleatorio para simular nebulosa
          particle.x += (Math.random() - 0.5) * 0.4;
          particle.y += (Math.random() - 0.5) * 0.4;
          
          // Extraer componentes de color para modificar opacidad
          const colorMatch = particle.color.match(/rgba\((\d+),\s*(\d+),\s*(\d+),\s*[\d.]+\)/);
          const r = colorMatch ? colorMatch[1] : 255;
          const g = colorMatch ? colorMatch[2] : 255;
          const b = colorMatch ? colorMatch[3] : 255;
          
          // Guardar el estado actual
          ctx.save();
          
          // Trasladar y rotar para efecto más complejo
          ctx.translate(particle.x, particle.y);
          ctx.rotate(particle.rotation);
          
          // Dibujar con efecto de nebulosa
          const gradient = ctx.createRadialGradient(
            0, 0, 0,
            0, 0, particle.size
          );
          
          gradient.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${opacity})`);
          gradient.addColorStop(0.4, `rgba(${r}, ${g}, ${b}, ${opacity * 0.3})`);
          gradient.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`);
          
          // Dibujar formas variadas para más interés visual
          const shapeType = Math.floor(particle.x * particle.y) % 3;
          
          ctx.fillStyle = gradient;
          
          if (shapeType === 0) {
            // Círculo estándar
            ctx.beginPath();
            ctx.arc(0, 0, particle.size, 0, Math.PI * 2);
            ctx.fill();
          } else if (shapeType === 1) {
            // Forma elíptica
            ctx.beginPath();
            ctx.ellipse(0, 0, particle.size, particle.size * 0.7, 0, 0, Math.PI * 2);
            ctx.fill();
          } else {
            // Forma de nube nebulosa (múltiples círculos superpuestos)
            for (let i = 0; i < 3; i++) {
              const offsetX = (Math.random() - 0.5) * particle.size * 0.5;
              const offsetY = (Math.random() - 0.5) * particle.size * 0.5;
              const radius = particle.size * (0.5 + Math.random() * 0.5);
              
              ctx.beginPath();
              ctx.arc(offsetX, offsetY, radius, 0, Math.PI * 2);
              ctx.fill();
            }
          }
          
          // Restaurar el estado
          ctx.restore();
          
          return particle;
        })
        .filter(particle => particle.life > 0);
      
      // Restaurar modo de composición predeterminado
      ctx.globalCompositeOperation = 'source-over';
      
      animationFrameRef.current = requestAnimationFrame(animate);
    }
    
    animate();
    
    // Limpieza
    return () => {
      window.removeEventListener('resize', resizeCanvas);
      window.removeEventListener('mousemove', handleMouseMove);
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed top-0 left-0 w-full h-full pointer-events-none z-50"
      style={{ pointerEvents: 'none', background: 'transparent' }}
    />
  );
}
