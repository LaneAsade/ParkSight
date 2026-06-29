// frontend/src/App.jsx
import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import OverviewPage from "./pages/OverviewPage";
import HotspotsPage from "./pages/HotspotsPage";
import HotspotDetailPage from "./pages/HotspotDetailPage";
import CongestionPage from "./pages/CongestionPage";
import PatrolPage from "./pages/PatrolPage";
import ForecastPage from "./pages/ForecastPage";
import EvidencePage from "./pages/EvidencePage";
import ScenariosPage from "./pages/ScenariosPage";
import ExecutivePage from "./pages/ExecutivePage";   // ← NEW
import NotFoundPage from "./pages/NotFoundPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<OverviewPage />} />
        <Route path="hotspots" element={<HotspotsPage />} />
        <Route path="hotspots/:clusterId" element={<HotspotDetailPage />} />
        <Route path="congestion" element={<CongestionPage />} />
        <Route path="patrol" element={<PatrolPage />} />
        <Route path="forecast" element={<ForecastPage />} />
        <Route path="evidence" element={<EvidencePage />} />
        <Route path="scenarios" element={<ScenariosPage />} />
        <Route path="executive" element={<ExecutivePage />} />   {/* ← NEW */}
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}