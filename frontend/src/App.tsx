import { Layout } from "@/components/layout/Layout";
import { Outlet } from "react-router-dom";

export function App() {
  return (
    <Layout>
      <Outlet />
    </Layout>
  );
}
