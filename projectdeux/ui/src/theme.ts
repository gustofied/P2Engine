export const theme = {
  fontFamily: "Roboto, sans-serif",

  headings: {
    fontFamily: "Instrument Serif, serif",
  },

  breakpoints: {
    xxs: 320,

    xs: 480,

    sm: 768,

    md: 1024,

    lg: 1280,

    xl: 1440,
  },

  colors: {
    lightPink: [
      "#ffe4e6",
      "#ffccd5",
      "#ffb3c2",
      "#ff99af",
      "#ff809c",
      "#ff6689",
      "#ff4d76",
      "#ff3363",
      "#ff1a50",
      "#ff003d",
    ],

    darkGray: [
      "#f5f5f5",
      "#e0e0e0",
      "#cccccc",
      "#b3b3b3",
      "#999999",
      "#808080",
      "#666666",
      "#4d4d4d",
      "#333333",
      "#1a1a1a",
    ],
  },

  primaryColor: "darkGray",

  globalStyles: () => ({
    body: {
      backgroundColor: "#f0f0f0",
    },
  }),

  components: {
    Button: {
      styles: () => ({
        root: {
          borderRadius: "8px",
        },
      }),
    },
  },
};
