import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { ImpactPage } from "./pages/ImpactPage";
import { ObjectListPage } from "./pages/ObjectListPage";
import { SelfLoopAnalysisPage } from "./pages/SelfLoopAnalysisPage";
import { ScanFailureSummaryPage } from "./pages/ScanFailureSummaryPage";
import { TableDetailPage } from "./pages/TableDetailPage";
import { TableSearchPage } from "./pages/TableSearchPage";

export default function App() {
  // Keep routing intentionally small for the MVP: search, detail, and impact.
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<TableSearchPage />} />
        <Route path="/analysis/cycles" element={<SelfLoopAnalysisPage />} />
        <Route path="/scan-failures" element={<ScanFailureSummaryPage />} />
        <Route path="/objects" element={<ObjectListPage />} />
        <Route path="/tables/:tableKey" element={<TableDetailPage />} />
        <Route path="/tables/:tableKey/impact" element={<ImpactPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
