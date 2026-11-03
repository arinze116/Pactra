import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#f4f4ef",
        "canvas-deep": "#e9ebe4",
        line: "#dde0d8",
        ink: {
          950: "#121713",
          800: "#29312b",
          700: "#3f4942",
          600: "#566159",
          500: "#6f7971",
          400: "#909890",
          300: "#b3b9b3"
        },
        pactra: {
          50: "#eef8f3",
          100: "#d9eee3",
          300: "#72c8a2",
          600: "#14805a",
          700: "#0b6748"
        },
        positive: "#249264",
        "positive-dark": "#176843",
        negative: "#c2413d",
        "negative-soft": "#fff2f1",
        warning: "#c58a2c",
        "warning-dark": "#845812",
        "warning-soft": "#fff8e9"
      },
      fontFamily: {
        sans: ["IBM Plex Sans Variable", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "SFMono-Regular", "Consolas", "monospace"]
      },
      boxShadow: {
        card: "0 1px 2px rgba(18, 23, 19, 0.04)",
        float: "0 24px 60px rgba(18, 23, 19, 0.18)"
      }
    }
  },
  plugins: []
} satisfies Config;
