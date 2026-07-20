import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { TasksProvider } from "./tasks";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <TasksProvider>
        <App />
      </TasksProvider>
    </BrowserRouter>
  </React.StrictMode>
);
