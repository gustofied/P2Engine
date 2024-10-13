import React from "react";
import ReactDOM from "react-dom";
import App from "./components/App";
import { MantineProvider } from "@mantine/core";
import { BrowserRouter } from "react-router-dom";

ReactDOM.render(
  <MantineProvider withNormalizeCSS withGlobalStyles>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </MantineProvider>,
  document.getElementById("root")
);
