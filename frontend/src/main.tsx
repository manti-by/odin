import { App } from "@/App";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider, createBrowserRouter } from "react-router-dom";
import "@/styles/app.css";
import "@/styles/components.css";
import "@/styles/responsive.css";

const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, lazy: async () => ({ Component: (await import("@/pages/DashboardPage")).DashboardPage }) },
      {
        path: "sensors/:location",
        lazy: async () => ({ Component: (await import("@/pages/SensorChartPage")).SensorChartPage }),
      },
      {
        path: "styleguide",
        lazy: async () => ({ Component: (await import("@/pages/StyleguidePage")).StyleguidePage }),
      },
      { path: "*", lazy: async () => ({ Component: (await import("@/pages/NotFoundPage")).NotFoundPage }) },
    ],
  },
]);

const root = document.getElementById("root");
if (!root) {
  throw new Error("Root element #root not found");
}

createRoot(root).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
