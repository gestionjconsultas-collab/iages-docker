import React, { useState } from 'react';
import { Sun, Moon, Sparkles } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

const ThemeToggle = () => {
  const { theme, setTheme, isDark } = useTheme();
  const [isHovered, setIsHovered] = useState(false);

  const handleToggle = () => {
    setTheme(isDark ? 'light' : 'dark');
  };

  return (
    <div className="flex items-center gap-3">
      {/* Label Premium */}
      <div className="hidden sm:flex flex-col items-end">
        <span className="text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
          Tema
        </span>
        <span className="text-[10px] text-gray-400 dark:text-gray-500 font-medium">
          {isDark ? 'Oscuro' : 'Claro'}
        </span>
      </div>
      
      {/* Toggle Switch Container con Glow */}
      <div className="relative">
        {/* Glow Effect Ring */}
        <div 
          className={`absolute inset-0 rounded-full transition-all duration-700 ${
            isHovered ? 'scale-125 opacity-100' : 'scale-100 opacity-60'
          }`}
          style={{
            background: isDark 
              ? 'radial-gradient(circle, rgba(249, 115, 22, 0.4) 0%, rgba(220, 38, 38, 0.2) 50%, transparent 70%)'
              : 'radial-gradient(circle, rgba(249, 115, 22, 0.6) 0%, rgba(220, 38, 38, 0.3) 50%, transparent 70%)',
            filter: 'blur(12px)',
          }}
        />

        {/* Main Toggle Button */}
        <button
          onClick={handleToggle}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          className={`relative inline-flex h-10 w-20 items-center rounded-full transition-all duration-500 ease-out focus:outline-none focus:ring-4 focus:ring-orange-400/50 dark:focus:ring-primary/50 transform ${
            isHovered ? 'scale-110' : 'scale-100'
          }`}
          style={{
            background: isDark 
              ? 'linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%)'
              : 'linear-gradient(135deg, #f97316 0%, #fb923c 50%, #dc2626 100%)',
            boxShadow: isDark 
              ? '0 8px 32px rgba(249, 115, 22, 0.4), inset 0 2px 8px rgba(0, 0, 0, 0.3)' 
              : '0 8px 32px rgba(249, 115, 22, 0.6), inset 0 2px 8px rgba(255, 255, 255, 0.3)',
          }}
          title={isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
        >
          {/* Slider Circle */}
          <span
            className={`relative inline-flex h-7 w-7 transform items-center justify-center rounded-full transition-all duration-500 ease-out ${
              isDark ? 'translate-x-11' : 'translate-x-1.5'
            }`}
            style={{
              background: 'linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)',
              boxShadow: isDark
                ? '0 4px 16px rgba(248, 250, 252, 0.4), 0 0 24px rgba(249, 115, 22, 0.3)'
                : '0 4px 16px rgba(0, 0, 0, 0.2), 0 0 16px rgba(249, 115, 22, 0.2)',
            }}
          >
            {/* Icon con efectos */}
            <div 
              className={`transform transition-all duration-500 ${
                isDark ? 'rotate-180 scale-110' : 'rotate-0 scale-100'
              }`}
            >
              {isDark ? (
                <Moon className="w-4 h-4 text-slate-700" strokeWidth={2.5} />
              ) : (
                <Sun className="w-4 h-4 text-primary" strokeWidth={2.5} />
              )}
            </div>

            {/* Sparkle effect cuando hover */}
            {isHovered && (
              <Sparkles 
                className="absolute -top-1 -right-1 w-3 h-3 text-orange-400 animate-pulse" 
                strokeWidth={3}
              />
            )}
          </span>

          {/* Background Icons (decorativos más grandes) */}
          <div className="absolute inset-0 flex items-center justify-between px-2 pointer-events-none">
            <Sun 
              className={`w-4 h-4 transition-all duration-500 ${
                isDark ? 'text-gray-600 opacity-30 scale-90' : 'text-white/70 opacity-0 scale-50'
              }`}
              strokeWidth={2.5}
            />
            <Moon 
              className={`w-4 h-4 transition-all duration-500 ${
                isDark ? 'text-orange-300 opacity-0 scale-50' : 'text-white/60 opacity-30 scale-90'
              }`}
              strokeWidth={2.5}
            />
          </div>

          {/* Shimmer effect */}
          <div 
            className="absolute inset-0 rounded-full overflow-hidden opacity-30"
            style={{
              background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.4) 50%, transparent 100%)',
              backgroundSize: '200% 100%',
              animation: 'shimmer 2s infinite',
            }}
          />
        </button>
      </div>
    </div>
  );
};

export default ThemeToggle;