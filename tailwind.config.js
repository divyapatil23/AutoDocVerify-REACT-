/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#070912",
        panel: "#101524",
        line: "#25304a",
        brand: "#6747ff",
      },
      boxShadow: {
        glow: "0 24px 70px rgba(103, 71, 255, 0.22)",
      },
    },
  },
  plugins: [],
};
