// App.tsx
import React from "react";
import { Routes, Route } from "react-router-dom";
import HomePage from "./HomePage";
import MainApp from "./MainApp";
import About from "./About"; // Import the About component
import NotFoundPage from "./NotFoundPage";
import { HeaderSimple } from "../components/HeaderSimple";

const App: React.FC = () => {
  return (
    <>
      <HeaderSimple />
      <div style={{ paddingTop: "56px" }}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/app" element={<MainApp />} />
          <Route path="/about" element={<About />} />{" "}
          {/* Add the About route */}
          <Route path="*" element={<NotFoundPage />} />{" "}
          {/* Handle unmatched routes */}
        </Routes>
      </div>
    </>
  );
};

export default App;
