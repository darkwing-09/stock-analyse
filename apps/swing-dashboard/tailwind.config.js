/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: { 950: "#0b0f1a", 900: "#0d1220", 850: "#121826", 800: "#182033", 700: "#232c42", 600: "#323d57" },
        fg: { DEFAULT: "#eef1f6", 2: "#a9b3c7", 3: "#7f8aa1" },
        marigold: { DEFAULT: "#f2b23e", deep: "#c98500", soft: "#f6c96e" },
        nifty: "#3987e5",
        good: "#0ca30c",
        bad: "#d03b3b",
      },
      fontFamily: {
        sans: ['"Geist Variable"', "system-ui", "sans-serif"],
        mono: ['"Geist Mono Variable"', "ui-monospace", "monospace"],
      },
      boxShadow: {
        lift: "0 12px 32px -12px rgba(0,0,0,0.55), 0 2px 6px -2px rgba(0,0,0,0.4)",
      },
    },
  },
  plugins: [],
};
