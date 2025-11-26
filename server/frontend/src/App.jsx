import React, { useEffect, useState } from "react";
import Layout from "./components/Layout";
import DatasetGrid from "./components/DatasetGrid";
import EDAStudio from "./components/EDAStudio";
import DriftStudio from "./components/DriftStudio";

const BACKEND = "http://localhost:8000";

export default function App() {
  const [datasets, setDatasets] = useState([]);
  const [view, setView] = useState("workspace"); // workspace | eda | drift
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
    </Layout>
  );
}