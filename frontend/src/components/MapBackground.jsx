import React from 'react';

const MapBackground = () => {
  return (
    <svg 
      className="hero-map-svg" 
      viewBox="0 0 1000 1000" 
      preserveAspectRatio="xMidYMid slice"
    >
      {/* Base road grid - horizontal */}
      <g className="map-roads-base">
        {[100, 180, 260, 340, 420, 500, 580, 660, 740, 820, 900].map((y, i) => (
          <path 
            key={`h${i}`}
            className={i % 3 === 0 ? "map-road-main" : "map-road"}
            d={`M 0 ${y} Q ${250 + Math.sin(i) * 50} ${y + Math.cos(i) * 30} 500 ${y + Math.sin(i * 2) * 20} T 1000 ${y}`}
          />
        ))}
        
        {/* Vertical roads */}
        {[80, 160, 240, 320, 400, 480, 560, 640, 720, 800, 880, 960].map((x, i) => (
          <path 
            key={`v${i}`}
            className={i % 4 === 0 ? "map-road-main" : "map-road"}
            d={`M ${x} 0 Q ${x + Math.cos(i) * 40} 250 ${x + Math.sin(i) * 30} 500 T ${x} 1000`}
          />
        ))}
        
        {/* Diagonal avenues */}
        <path className="map-road-main" d="M 0 0 Q 300 350 500 500 T 1000 1000" />
        <path className="map-road-main" d="M 1000 0 Q 700 350 500 500 T 0 1000" />
        <path className="map-road" d="M 200 0 Q 400 300 500 500 T 800 1000" />
        <path className="map-road" d="M 800 0 Q 600 300 500 500 T 200 1000" />
      </g>
      
      {/* Curved secondary roads */}
      <g className="map-roads-secondary">
        <path className="map-road" d="M 0 200 C 200 180 300 350 500 300 S 800 400 1000 350" />
        <path className="map-road" d="M 0 600 C 150 620 400 550 500 600 S 750 650 1000 580" />
        <path className="map-road" d="M 300 0 C 280 200 400 400 350 500 S 320 700 380 1000" />
        <path className="map-road" d="M 700 0 C 720 180 650 350 680 500 S 700 750 660 1000" />
      </g>
      
      {/* Glowing main routes - animated */}
      <g className="map-routes-glow">
        {/* Route 1 - Main journey */}
        <path 
          className="map-route-glow"
          d="M 150 250 C 250 280 350 200 450 350 S 600 300 700 450 S 850 400 900 550"
        />
        
        {/* Route 2 - Secondary */}
        <path 
          className="map-route-glow-2"
          d="M 100 400 Q 300 350 400 500 T 600 450 T 850 600"
        />
        
        {/* Pulsing highlight route */}
        <path 
          className="map-route-pulse"
          d="M 200 300 C 300 320 400 280 500 400"
        />
      </g>
      
      {/* Ring roads */}
      <ellipse 
        cx="500" cy="500" rx="350" ry="300" 
        className="map-road-main" 
        style={{ fill: 'none' }}
      />
      <ellipse 
        cx="500" cy="500" rx="200" ry="170" 
        className="map-road" 
        style={{ fill: 'none' }}
      />
      
      {/* Intersection highlights */}
      {[[320, 340], [500, 500], [680, 420], [400, 600], [600, 350]].map(([x, y], i) => (
        <circle 
          key={`int${i}`}
          cx={x} cy={y} r="4"
          fill="rgba(125, 211, 252, 0.3)"
        />
      ))}
    </svg>
  );
};

export default MapBackground;
