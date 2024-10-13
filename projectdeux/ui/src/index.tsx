// index.tsx
import React from "react";
import ReactDOM from "react-dom";
import App from "./pages/App";
import { MantineProvider } from "@mantine/core";
import { BrowserRouter } from "react-router-dom";
import { theme } from "./theme";

ReactDOM.render(
  <MantineProvider theme={theme} withNormalizeCSS withGlobalStyles>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </MantineProvider>,
  document.getElementById("root")
);
