import { Header } from "@/components/Header";
import { Outlet } from "react-router-dom";

export function App() {
  return (
    <>
      <Header />
      <main className="container">
        <Outlet />
      </main>
    </>
  );
}
