import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef5ff',
          100: '#dae9ff',
          200: '#b6d3ff',
          300: '#84b2ff',
          400: '#528bff',
          500: '#2f68f6',
          600: '#1f4dd3',
          700: '#1d3ea9',
          800: '#1d3886',
          900: '#1f336e'
        }
      }
    }
  },
  plugins: []
} satisfies Config;
