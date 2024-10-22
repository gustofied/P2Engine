export const theme: MantineThemeOverride = {
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
      "#363946", // lightest gray
      "#363946", // very light gray
      "#363946", // light gray
      "#363946", // medium-light gray
      "#363946", // medium gray
      "#363946", // dark gray (your desired mid-tone)
      "#666666", // slightly lighter dark gray
      "#363946", // darker gray
      "#363946", // very dark gray
      "#363946", // darkest gray
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
      styles: (theme: { colors: { darkGray: any[] } }) => ({
        root: {
          backgroundColor: theme.colors.darkGray[0], // Set default state color to #363946
          "&:hover": {
            backgroundColor: theme.colors.darkGray[0], // Set hover state color to #363946
          },
          "&:active": {
            backgroundColor: theme.colors.darkGray[0], // Set active state color to #363946
          },
          "&:disabled": {
            backgroundColor: theme.colors.darkGray[2], // Optional: Set disabled state if needed
          },
        },
      }),
    },
  },
};
