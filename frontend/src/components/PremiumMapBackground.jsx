import React, { useMemo } from 'react';

const PremiumMapBackground = () => {
  // Generate random particles
  const particles = useMemo(() => {
    return Array.from({ length: 20 }, (_, i) => ({
      id: i,
      left: `${Math.random() * 100}%`,
      delay: `${Math.random() * 15}s`,
      duration: `${15 + Math.random() * 10}s`,
      size: 2 + Math.random() * 3
    }));
  }, []);

  // Generate neon routes
  const routes = useMemo(() => {
    return [
      { top: '20%', left: '10%', width: '200px', rotate: '15deg', delay: '0s' },
      { top: '35%', left: '60%', width: '250px', rotate: '-20deg', delay: '1s' },
      { top: '55%', left: '20%', width: '180px', rotate: '45deg', delay: '2s' },
      { top: '70%', left: '50%', width: '220px', rotate: '-10deg', delay: '0.5s' },
      { top: '15%', left: '70%', width: '150px', rotate: '30deg', delay: '1.5s' },
      { top: '80%', left: '5%', width: '280px', rotate: '-25deg', delay: '2.5s' },
    ];
  }, []);

  return (
    <div className="gps-map-bg">
      {/* Animated Grid */}
      <div className="gps-grid" />
      
      {/* Radial Gradient Overlay */}
      <div 
        className="absolute inset-0"
        style={{
          background: 'radial-gradient(circle at 50% 30%, rgba(0, 229, 255, 0.08) 0%, transparent 50%)'
        }}
      />
      
      {/* Neon Routes */}
      {routes.map((route, i) => (
        <div
          key={i}
          className="neon-route"
          style={{
            top: route.top,
            left: route.left,
            width: route.width,
            transform: `rotate(${route.rotate})`,
            animationDelay: route.delay
          }}
        />
      ))}
      
      {/* Floating Particles */}
      <div className="particles-container">
        {particles.map((p) => (
          <div
            key={p.id}
            className="particle"
            style={{
              left: p.left,
              width: `${p.size}px`,
              height: `${p.size}px`,
              animationDelay: p.delay,
              animationDuration: p.duration
            }}
          />
        ))}
      </div>
      
      {/* Corner Accents */}
      <div 
        className="absolute top-0 left-0 w-64 h-64"
        style={{
          background: 'radial-gradient(circle at 0% 0%, rgba(0, 229, 255, 0.1) 0%, transparent 70%)'
        }}
      />
      <div 
        className="absolute bottom-0 right-0 w-64 h-64"
        style={{
          background: 'radial-gradient(circle at 100% 100%, rgba(10, 132, 255, 0.1) 0%, transparent 70%)'
        }}
      />
    </div>
  );
};

export default PremiumMapBackground;
