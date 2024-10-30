// App.tsx
import React from "react";
import { BrowserRouter as Router, Route, Switch } from "react-router-dom";
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
        <Switch>
          <Route exact path="/" component={HomePage} />
          <Route path="/app" component={MainApp} />
          <Route path="/about" component={About} /> {/* About route */}
          <Route component={NotFoundPage} /> {/* Handle unmatched routes */}
        </Switch>
      </div>
    </>
  );
};

export default App;
