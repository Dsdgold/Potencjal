import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        sig: {
          red: "#e63946",
          "red-dark": "#b30839",
          bg: "#0a0a12",
          surface: "#12121e",
          card: "#16162a",
          border: "#252540",
          muted: "#7878a0",
          text: "#e8e8f4",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
