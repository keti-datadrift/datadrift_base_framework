import React, { useEffect, useState } from "react";
import Layout from "./components/Layout";
import DatasetGrid from "./components/DatasetGrid";
import EDAStudio from "./components/EDAStudio";
import DriftStudio from "./components/DriftStudio";
import ZipDetail from "./components/ZipDetail";

const BACKEND = "http://localhost:8000";

export default function App() {
  const [datasets, setDatasets] = useState([]);

  // Drift
  const [compareBase, setCompareBase] = useState(null);
  const [compareTarget, setCompareTarget] = useState(null);

  // view modes: workspace | eda | drift | zipDetail | selectTarget
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
          driftMode={false} // 일반 Workspace 모드
        />
      )}

      {/* 비교 대상 선택 */}
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
        />
      )}
    </Layout>
  );
}