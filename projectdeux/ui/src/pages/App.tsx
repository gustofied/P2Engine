// App.tsx

import React from "react";
import { Route, Switch } from "react-router-dom";
import HomePage from "./HomePage";
import MainApp from "./MainApp";
import About from "./About";
import NotFoundPage from "./NotFoundPage";
import { HeaderSimple } from "../components/HeaderSimple";

const App: React.FC = () => {
  return (
    <>
      <HeaderSimple />
      <div style={{ paddingTop: "70px" }}>
        {" "}
        {/* Adjusted paddingTop to match header height */}
        <Switch>
          <Route exact path="/" component={HomePage} />
          <Route path="/app" component={MainApp} />
          <Route path="/about" component={About} />
          <Route component={NotFoundPage} />
        </Switch>
      </div>
    </>
  );
};

export default App;
