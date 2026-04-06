/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  darkMode: 'class', // ← ESTA ES LA LÍNEA IMPORTANTE
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        // Colores dinámicos del tenant usando CSS variables
        primary: {
          DEFAULT: 'var(--color-primary, #FF6B35)',
          hover: 'var(--color-primary-hover, #e55a2b)',
          light: 'var(--color-primary-light, #ffb8a0)',
          dark: 'var(--color-primary-dark, #cc5529)',
        },
        secondary: {
          DEFAULT: 'var(--color-secondary, #004E89)',
          hover: 'var(--color-secondary-hover, #003d6e)',
          light: 'var(--color-secondary-light, #4d8ab8)',
          dark: 'var(--color-secondary-dark, #003355)',
        },
        accent: {
          DEFAULT: 'var(--color-accent, #F7B801)',
          hover: 'var(--color-accent-hover, #dd9f00)',
          light: 'var(--color-accent-light, #ffd966)',
        },
        // Mantener colores de Tailwind por defecto para otros usos
        orange: {
          50: '#fff7ed',
          100: '#ffedd5',
          200: '#fed7aa',
          300: '#fdba74',
          400: '#fb923c',
          500: '#f97316',
          600: '#ea580c',
          700: '#c2410c',
          800: '#9a3412',
          900: '#7c2d12',
        },
      },
      animation: {
        'slide-in': 'slideInRight 0.3s ease-out',
        'slide-out': 'slideOutRight 0.3s ease-in',
        'fade-in': 'fadeIn 0.2s ease-out',
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
      },
      keyframes: {
        slideInRight: {
          '0%': { transform: 'translateX(100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        slideOutRight: {
          '0%': { transform: 'translateX(0)', opacity: '1' },
          '100%': { transform: 'translateX(100%)', opacity: '0' },
        },
        fadeIn: {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}