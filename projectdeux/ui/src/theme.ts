// theme.ts

import { MantineThemeOverride, MantineTheme } from "@mantine/core";

export const theme: MantineThemeOverride = {
  fontFamily: "Roboto, sans-serif",

  headings: {
    fontFamily: "Instrument Serif, serif", // Reverted to original font
    fontWeight: 700,
  },

  breakpoints: {
    xs: 480,
    sm: 768,
    md: 1024,
    lg: 1280,
    xl: 1440,
  },

  colors: {
    darkGray: [
      "#f0f0f4", // index 0
      "#d9d9e1", // index 1
      "#c2c2cf", // index 2
      "#ababbd", // index 3
      "#9494aa", // index 4
      "#7d7d98", // index 5
      "#363946", // index 6, set to #363946
      "#2f313e", // index 7
      "#282a36", // index 8
      "#21222c", // index 9
    ],
  },

  primaryColor: "darkGray",
  primaryShade: 6,

  globalStyles: () => ({
    body: {
      backgroundColor: "#ffffff",
    },
  }),

  components: {
    Button: {
      styles: (theme: MantineTheme) => ({
        root: {
          backgroundColor: theme.colors.darkGray[6],
          color: "#ffffff",
          borderRadius: theme.radius.md,
          fontWeight: 500,
          "&:hover": {
            backgroundColor: theme.fn.darken(theme.colors.darkGray[6], 0.1),
          },
        },
      }),
    },
    Title: {
      styles: {
        root: {
          color: "#2C3E50",
        },
      },
    },
    Text: {
      styles: {
        root: {
          color: "#4A4A4A",
        },
      },
    },
  },
};
