import React, { useEffect, useState } from "react";
import Layout from "./components/Layout";
import DatasetGrid from "./components/DatasetGrid";
import EDAStudio from "./components/EDAStudio";
import DriftStudio from "./components/DriftStudio";
import ZipDetail from "./components/ZipDetail";
import WorkspaceStudio from "./components/WorkspaceStudio";
import { Routes, Route, useNavigate, useLocation } from "react-router-dom";

// 리버스 프록시 환경: 상대 경로 사용
const BACKEND = "/api";

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [datasets, setDatasets] = useState([]);

  // Drift
  const [compareBase, setCompareBase] = useState(null);
  const [compareTarget, setCompareTarget] = useState(null);

  // View state (used in Home route)
  const [view, setView] = useState("workspace");
  const [selectedDataset, setSelectedDataset] = useState(null);

  const fetchDatasets = () => {
    fetch(`${BACKEND}/datasets`)
      .then((r) => r.json())
      .then(setDatasets);
  };

  useEffect(() => {
    fetchDatasets();
  }, []);

  return (
    <Layout>
      <Routes>
        <Route
          path="/"
          element={
            <>
              {view === "workspace" && (
                <DatasetGrid
                  datasets={datasets}
                  backend={BACKEND}
                  refresh={fetchDatasets}
                  onEDA={(ds) => {
                    setSelectedDataset(ds);
                    setView("eda");
                  }}
                  onDrift={(ds) => {
                    setCompareBase(ds);
                    setView("selectTarget");
                  }}
                  onSelect={(ds) => {
                    if (ds.type === "zip") {
                      setSelectedDataset(ds);
                      setView("zipDetail");
                    } else {
                      setSelectedDataset(ds);
                      setView("eda");
                    }
                  }}
                  driftMode={false}
                />
              )}

              {view === "selectTarget" && (
                <DatasetGrid
                  datasets={datasets}
                  backend={BACKEND}
                  title="비교 대상 데이터셋 선택"
                  driftMode={true}
                  compareBase={compareBase}
                  onSelectTarget={(ds) => {
                    setCompareTarget(ds);
                    setView("drift");
                  }}
                  onBack={() => setView("workspace")}
                />
              )}

              {view === "eda" && selectedDataset && (
                <EDAStudio
                  backend={BACKEND}
                  dataset={selectedDataset}
                  onBack={() => setView("workspace")}
                />
              )}

              {view === "drift" && compareBase && compareTarget && (
                <DriftStudio
                  backend={BACKEND}
                  baseDataset={compareBase}
                  targetDataset={compareTarget}
                  onBack={() => setView("workspace")}
                />
              )}

              {view === "zipDetail" && selectedDataset && (
                <ZipDetail
                  backend={BACKEND}
                  dataset={selectedDataset}
                  onBack={() => setView("workspace")}
                  onOpenEDA={() => setView("eda")}
                />
              )}
            </>
          }
        />
        <Route
          path="/workspace"
          element={
            <WorkspaceStudio
              datasets={datasets}
              onBack={() => {
                // if came from direct nav, go home
                if (location.key !== "default") {
                  navigate(-1);
                } else {
                  navigate("/");
                }
              }}
            />
          }
        />
      </Routes>
    </Layout>
  );
}