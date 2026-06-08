import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ana: "#60a5fa",
        jal: "#f87171",
        thai: "#fbbf24",
      },
    },
  },
  plugins: [],
};
export default config;
