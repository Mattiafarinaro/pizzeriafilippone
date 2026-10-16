/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html"],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Playfair Display"', "serif"],
        body: ['"Plus Jakarta Sans"', "sans-serif"],
      },
      colors: {
        brand: { DEFAULT: "#C1440E", dark: "#8B2E07", light: "#E85D20" },
        ink: { DEFAULT: "#1A120B", muted: "#6B5744" },
        cream: { DEFAULT: "#FBF9F7", dark: "#F0E8D8" },
        wa: "#25D366",
      },
    },
  },
  plugins: [],
};
