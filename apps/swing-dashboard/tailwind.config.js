/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ground: "#080808",
        surface: { DEFAULT: "#0f0f0f", 2: "#141414", 3: "#1a1a1a" },
        line: { DEFAULT: "rgba(255,255,255,0.08)", strong: "rgba(255,255,255,0.14)" },
        fg: { DEFAULT: "#ededed", 2: "#a1a1aa", 3: "#8b8b8b" },
        accent: { DEFAULT: "#3b82f6", soft: "#60a5fa", pale: "#93c5fd" },
        series: { strategy: "#3b82f6", nifty: "#d95926", aqua: "#199e70", yellow: "#c98500" },
        good: "#0ca30c",
        bad: "#d03b3b",
      },
      fontFamily: {
        sans: ['"Geist Variable"', "system-ui", "sans-serif"],
        mono: ['"Geist Mono Variable"', "ui-monospace", "monospace"],
      },
      boxShadow: {
        lift: "0 16px 40px -16px rgba(0,0,0,0.7), 0 2px 8px -2px rgba(0,0,0,0.5)",
        bar: "0 8px 24px -8px rgba(0,0,0,0.8)",
      },
      transitionTimingFunction: {
        expo: "cubic-bezier(0.16, 1, 0.3, 1)",
        quint: "cubic-bezier(0.23, 1, 0.32, 1)",
      },
      keyframes: {
        shimmer: { "0%": { backgroundPosition: "-200% 0" }, "100%": { backgroundPosition: "200% 0" } },
      },
      animation: { shimmer: "shimmer 1.8s linear infinite" },
    },
  },
  plugins: [],
};
