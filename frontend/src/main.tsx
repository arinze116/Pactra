import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./pactra.css";
import "@fontsource-variable/ibm-plex-sans";
import App from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
