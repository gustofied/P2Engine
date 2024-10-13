import React from "react";
import { Routes, Route } from "react-router-dom";
import HomePage from "./HomePage";
import MainApp from "./MainApp";

const App: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/app" element={<MainApp />} />
    </Routes>
  );
};

export default App;
