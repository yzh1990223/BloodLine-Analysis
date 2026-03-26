import { Navigate, Route, Routes } from "react-router-dom";
import { ImpactPage } from "./pages/ImpactPage";
import { TableDetailPage } from "./pages/TableDetailPage";
import { TableSearchPage } from "./pages/TableSearchPage";

export default function App() {
  // Keep routing intentionally small for the MVP: search, detail, and impact.
  return (
    <Routes>
      <Route path="/" element={<TableSearchPage />} />
      <Route path="/tables/:tableKey" element={<TableDetailPage />} />
      <Route path="/tables/:tableKey/impact" element={<ImpactPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
