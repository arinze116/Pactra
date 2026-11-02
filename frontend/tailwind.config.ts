import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#080b12",
          900: "#0d111b",
          850: "#111722",
          800: "#171e2b"
        },
        pactra: {
          300: "#71f5cf",
          400: "#3ee6b4",
          500: "#18c997",
          600: "#10a77d"
        }
      },
      boxShadow: {
        panel: "0 24px 70px rgba(0, 0, 0, 0.24)",
        glow: "0 0 0 1px rgba(62, 230, 180, 0.1), 0 14px 50px rgba(24, 201, 151, 0.08)"
      },
      backgroundImage: {
        "page-glow": "radial-gradient(circle at 15% 0%, rgba(44, 211, 162, 0.10), transparent 35%), radial-gradient(circle at 100% 10%, rgba(115, 98, 255, 0.09), transparent 28%)"
      }
    }
  },
  plugins: []
} satisfies Config;
