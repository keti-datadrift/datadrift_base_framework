import React, { useState, useEffect } from "react";
import DatasetWorkspace from "./components/DatasetWorkspace";
import EDAStudio from "./components/EDAStudio";
import DriftStudio from "./components/DriftStudio";

export default function App() {
  const [view, setView] = useState("workspace"); // workspace | eda | drift
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [datasets, setDatasets] = useState([]);

  useEffect(() => {
    fetch("http://localhost:8000/datasets")
      .then((res) => res.json())
      .then(setDatasets);
  }, []);

  const refreshDatasets = () => {
    fetch("http://localhost:8000/datasets")
      .then((res) => res.json())
      .then(setDatasets);
  };

  return (
    <div style={{ padding: 20 }}>
      {view === "workspace" && (
        <DatasetWorkspace
          datasets={datasets}
          onUploaded={refreshDatasets}
          onSelect={(ds) => {
            setSelectedDataset(ds);
            setView("eda");
          }}
          onCompare={(ds) => {
            setSelectedDataset(ds);
            setView("drift");
          }}
        />
      )}

      {view === "eda" && (
        <EDAStudio dataset={selectedDataset} goBack={() => setView("workspace")} />
      )}

      {view === "drift" && (
        <DriftStudio dataset={selectedDataset} goBack={() => setView("workspace")} />
      )}
    </div>
  );
}