/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#090d16',
        card: '#0f172a',
        border: '#1e293b',
        primary: {
          DEFAULT: '#3b82f6',
          foreground: '#ffffff',
        },
        profit: '#10b981',
        loss: '#ef4444',
      }
    },
  },
  plugins: [],
}

