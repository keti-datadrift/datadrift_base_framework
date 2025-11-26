import React, { useEffect, useState } from "react";
import Layout from "./components/Layout";
import DatasetGrid from "./components/DatasetGrid";
import EDAStudio from "./components/EDAStudio";
import DriftStudio from "./components/DriftStudio";
import ZipDetail from "./components/ZipDetail";

const BACKEND = "http://localhost:8000";

export default function App() {
  const [datasets, setDatasets] = useState([]);
  const [view, setView] = useState("workspace"); // workspace | eda | drift | zipDetail
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
            setSelectedDataset(ds);
            setView("drift");
          }}
          onSelect={(ds) => {
            if (ds.type === "zip") {
              setSelectedDataset(ds);
              setView("zipDetail");
            } else {
              // 추후 일반 Detail Page 추가 가능
              setSelectedDataset(ds);
              setView("eda");
            }
          }}
        />
      )}

      {view === "eda" && selectedDataset && (
        <EDAStudio
          backend={BACKEND}
          dataset={selectedDataset}
          onBack={() => setView("workspace")}
        />
      )}

      {view === "drift" && selectedDataset && (
        <DriftStudio
          backend={BACKEND}
          dataset={selectedDataset}
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