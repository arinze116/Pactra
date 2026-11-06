import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#050506",
        "canvas-deep": "#020203",
        surface: "#0b0b0d",
        "surface-raised": "#141416",
        line: "#232326",
        ink: {
          950: "#f7f7f8",
          800: "#dedee1",
          700: "#c1c1c7",
          600: "#b0b0b8",
          500: "#9898a1",
          400: "#85858e",
          300: "#72727b"
        },
        pactra: {
          50: "#21060c",
          100: "#350811",
          300: "#ff6b82",
          600: "#e0002b",
          700: "#f11942"
        },
        positive: "#10b981",
        "positive-dark": "#6ee7b7",
        negative: "#f87171",
        "negative-soft": "#260d0d",
        warning: "#eab308",
        "warning-dark": "#fde047",
        "warning-soft": "#211b05"
      },
      fontFamily: {
        sans: ["IBM Plex Sans Variable", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "SFMono-Regular", "Consolas", "monospace"]
      },
      boxShadow: {
        card: "inset 0 1px 0 rgba(255,255,255,0.035)",
        float: "0 24px 80px rgba(0,0,0,0.48)"
      }
    }
  },
  plugins: []
} satisfies Config;
