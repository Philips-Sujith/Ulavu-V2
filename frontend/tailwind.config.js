/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        agri: {
          50: '#F0FDF4',
          100: '#DCFCE7',
          200: '#BBF7D0',
          300: '#86EFAC',
          400: '#4ADE80',
          500: '#2D6A4F',  // Primary deep agricultural green
          600: '#1B4332',  // Dark forest green
          700: '#143627',
          800: '#0E261B',
          900: '#081710',
          emerald: '#40916C',
          leaf: '#52B788',
        },
        ochre: {
          50: '#FEF9EF',
          100: '#FDF2D9',
          200: '#FBE4B3',
          300: '#F7D187',
          400: '#F4BE5B',
          500: '#E9C46A',  // Signature warm mustard/ochre
          600: '#D9A74A',
          700: '#B88232',
          800: '#8F6126',
        },
        earth: {
          sand: '#FAF9F6',
          clay: '#F4A261',
          terracotta: '#E76F51',
          stone: '#FAFAF9',
          card: '#FFFFFF',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
