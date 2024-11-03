// theme.ts

import { MantineThemeOverride, MantineTheme } from "@mantine/core";

export const theme: MantineThemeOverride = {
  fontFamily: "Inter, sans-serif",

  headings: {
    fontFamily: "Montserrat, sans-serif",
    fontWeight: 700,
  },

  colors: {
    brand: [
      "#f0f4f8", // Lightest
      "#d9e2ec",
      "#bcccdc",
      "#9fb3c8",
      "#829ab1",
      "#627d98",
      "#486581", // Primary color (index 6)
      "#334e68",
      "#243b53",
      "#102a43", // Darkest
    ],
  },

  primaryColor: "brand",
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
          backgroundColor: theme.colors.brand[6],
          color: "#ffffff",
          borderRadius: theme.radius.md,
          fontWeight: 600,
          "&:hover": {
            backgroundColor: theme.colors.brand[7],
          },
        },
      }),
    },
    Title: {
      styles: {
        root: {
          color: "#102a43", // Darkest shade from brand colors
        },
      },
    },
    Text: {
      styles: {
        root: {
          color: "#334e68", // Mid-dark shade from brand colors
        },
      },
    },
  },
};
