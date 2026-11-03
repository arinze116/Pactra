import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#0c100c",
        "canvas-deep": "#101510",
        surface: "#151a15",
        "surface-raised": "#1b211b",
        line: "#293129",
        ink: {
          950: "#f3f6ee",
          800: "#d9dfd3",
          700: "#bdc6b9",
          600: "#a0aa9d",
          500: "#7f8a7d",
          400: "#626d60",
          300: "#495448"
        },
        pactra: {
          50: "#182118",
          100: "#22301f",
          300: "#9fdc55",
          600: "#b8ff5a",
          700: "#ccff87"
        },
        positive: "#68d391",
        "positive-dark": "#8be0aa",
        negative: "#f06d69",
        "negative-soft": "#2a1717",
        warning: "#e4b860",
        "warning-dark": "#f0ca7b",
        "warning-soft": "#2a2214"
      },
      fontFamily: {
        sans: ["IBM Plex Sans Variable", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "SFMono-Regular", "Consolas", "monospace"]
      },
      boxShadow: {
        card: "inset 0 1px 0 rgba(255,255,255,0.025)",
        float: "0 20px 48px rgba(0,0,0,0.32)"
      }
    }
  },
  plugins: []
} satisfies Config;
