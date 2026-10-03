/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ink: { DEFAULT: "#0f172a", soft: "#334155" },
        accent: { DEFAULT: "#0e7490", dark: "#22d3ee" },
      },
    },
  },
  plugins: [],
};
