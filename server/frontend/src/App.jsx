import React, { useEffect, useState } from "react";
import Layout from "./components/Layout";
import DatasetGrid from "./components/DatasetGrid";
import DatasetDetail from "./components/DatasetDetail";
import EDAStudio from "./components/EDAStudio";
import DriftStudio from "./components/DriftStudio";

const BACKEND = "http://localhost:8000";

export default function App() {
  const [datasets, setDatasets] = useState([]);
  const [view, setView] = useState("workspace"); // workspace | detail | eda | drift
  const [selectedDataset, setSelectedDataset] = useState(null);

  const fetchDatasets = () => {
    fetch(`${BACKEND}/datasets`)
      .then((r) => r.json())
      .then(setDatasets)
      .catch((e) => console.error("Failed to load datasets", e));
  };

  useEffect(() => {
    fetchDatasets();
  }, []);

  const handleSelect = (ds) => {
    setSelectedDataset(ds);
    setView("detail");
  };

  return (
    <Layout>
      {view === "workspace" && (
        <DatasetGrid
          datasets={datasets}
          backend={BACKEND}
          refresh={fetchDatasets}
          onSelect={handleSelect}
          onEDA={(ds) => {
            setSelectedDataset(ds);
            setView("eda");
          }}
          onDrift={(ds) => {
            setSelectedDataset(ds);
            setView("drift");
          }}
        />
      )}

      {view === "detail" && selectedDataset && (
        <DatasetDetail
          backend={BACKEND}
          dataset={selectedDataset}
          onBack={() => setView("workspace")}
          onOpenEDA={() => setView("eda")}
          onOpenDrift={() => setView("drift")}
        />
      )}

      {view === "eda" && selectedDataset && (
        <EDAStudio
          backend={BACKEND}
          dataset={selectedDataset}
          onBack={() => setView("detail")}
        />
      )}

      {view === "drift" && selectedDataset && (
        <DriftStudio
          backend={BACKEND}
          dataset={selectedDataset}
          onBack={() => setView("detail")}
        />
      )}
    </Layout>
  );
}
