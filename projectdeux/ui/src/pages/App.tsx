// App.tsx
import React from "react";
import { Routes, Route } from "react-router-dom";
import HomePage from "./HomePage";
import MainApp from "./MainApp";
import { HeaderSimple } from "../components/HeaderSimple";

const App: React.FC = () => {
  return (
    <>
      <HeaderSimple />
      <div style={{ paddingTop: "56px" }}>
        {" "}
        {/* Add top padding here */}
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/app" element={<MainApp />} />
        </Routes>
      </div>
    </>
  );
};

export default App;
