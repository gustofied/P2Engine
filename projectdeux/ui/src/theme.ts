// theme.ts
export const theme = {
  fontFamily: "Roboto, sans-serif",
  headings: { fontFamily: "Instrument Serif, serif" },
  breakpoints: {
    xxs: 384,
    xs: 480,
    sm: 768,
    md: 1024,
    lg: 1440, // Increased from 1200 to 1440
    xl: 1600, // Increased from 1440 to 1600
  },
  colors: {
    lightPink: ["#F7F0F5"],
    darkGray: [
      "#363946",
      "#4b4f5e",
      "#616676",
      "#777E8E",
      "#8D95A6",
      "#A3ACBE", // Added additional shades if needed
    ],
  },
  primaryColor: "darkGray",
  globalStyles: () => ({
    body: {
      backgroundColor: "#F7F0F5",
      margin: 0,
      padding: 0,
      minHeight: "100vh",
    },
  }),
  // Added default container sizes
  components: {
    Container: {
      defaultProps: {
        sizes: {
          xs: 540,
          sm: 720,
          md: 960, // Increased from 768 to 960
          lg: 1140, // Increased from 1024 to 1140
          xl: 1320, // Increased from 1200 to 1320
        },
      },
    },
  },
};
