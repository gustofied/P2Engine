// theme.ts
export const theme = {
  fontFamily: "Roboto, sans-serif",
  headings: { fontFamily: "Instrument Serif, serif" },
  breakpoints: {
    xxs: 384,
    xs: 480,
    sm: 768,
    md: 1024,
    lg: 1200,
    xl: 1440,
  },
  colors: {
    lightPink: ["#F7F0F5"],
    darkGray: [
      "#363946", // Darkest shade
      "#4b4f5e", // Add more shades for gradient effect, etc.
      "#616676",
      "#777E8E",
      "#8D95A6",
    ],
  },
  primaryColor: "darkGray", // Set the primary color to darkGray if desired
  globalStyles: () => ({
    body: {
      backgroundColor: "#F7F0F5",
      margin: 0,
      padding: 0,
      minHeight: "100vh",
    },
  }),
};
