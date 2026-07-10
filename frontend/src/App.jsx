import { useState } from "react";
import Header from "./components/Header";
import UploadSection from "./components/UploadSection";
import ResultsDashboard from "./components/ResultsDashboard";
import ProcessingOverlay from "./components/ProcessingOverlay";
import TemplateUploader from "./components/TemplateUploader";
import axios from "axios";
import toast from "react-hot-toast";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const REQUIRED_FIELDS = [
  {
    key: "seller_aadhaar",
    label: "Seller Aadhaar",
    description: "Front or both sides of the seller's Aadhaar card",
    accept: "image/*,.pdf",
    icon: "id",
    group: "seller",
  },
  {
    key: "seller_pan",
    label: "Seller PAN",
    description: "Clear image of the seller's PAN card",
    accept: "image/*,.pdf",
    icon: "credit",
    group: "seller",
  },
  {
    key: "buyer_aadhaar",
    label: "Buyer Aadhaar",
    description: "Front or both sides of the buyer's Aadhaar card",
    accept: "image/*,.pdf",
    icon: "id",
    group: "buyer",
  },
  {
    key: "buyer_pan",
    label: "Buyer PAN",
    description: "Clear image of the buyer's PAN card",
    accept: "image/*,.pdf",
    icon: "credit",
    group: "buyer",
  },
  {
    key: "property_document",
    label: "Property Document",
    description: "Sale deed, property passbook, or registration document",
    accept: "image/*,.pdf",
    icon: "property",
    group: "property",
  },
];

function App() {
  const [files, setFiles] = useState({});
  const [results, setResults] = useState(null);
  const [errors, setErrors] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStep, setProcessingStep] = useState("");

  const handleFileSelect = (fieldKey, file) => {
    setFiles((prev) => ({ ...prev, [fieldKey]: file }));
  };

  const handleFileRemove = (fieldKey) => {
    setFiles((prev) => {
      const updated = { ...prev };
      delete updated[fieldKey];
      return updated;
    });
  };

  const allFilesUploaded = REQUIRED_FIELDS.every((f) => files[f.key]);

  const handleSubmit = async () => {
    if (!allFilesUploaded) {
      toast.error("Please upload all required documents.");
      return;
    }

    setIsProcessing(true);
    setResults(null);
    setErrors(null);
    setProcessingStep("Uploading documents...");

    const formData = new FormData();
    REQUIRED_FIELDS.forEach((field) => {
      formData.append(field.key, files[field.key]);
    });

    try {
      setProcessingStep("Processing with OCR & AI...");
      const response = await axios.post(
        `${API_URL}/process-documents`,
        formData,
        {
          timeout: 300000,
        }
      );

      console.log("Backend response:", response.data);

      const data = response.data;
      setResults(data.registry);

      if (data.errors && Object.keys(data.errors).length > 0) {
        setErrors(data.errors);
        toast.error("Some documents could not be processed.");
      } else {
        toast.success("All documents processed successfully!");
      }
    } catch (err) {
      console.error("API error:", err);
      const message =
        err.response?.data?.detail || err.message || "Something went wrong.";
      toast.error(message);
    } finally {
      setIsProcessing(false);
      setProcessingStep("");
    }
  };

  const handleReset = () => {
    setFiles({});
    setResults(null);
    setErrors(null);
  };

  return (
    <div className="app-container">
      <Header />

      <main className="main-content">
        {!results ? (
          <UploadSection
            fields={REQUIRED_FIELDS}
            files={files}
            onFileSelect={handleFileSelect}
            onFileRemove={handleFileRemove}
            onSubmit={handleSubmit}
            allFilesUploaded={allFilesUploaded}
            isProcessing={isProcessing}
          />
        ) : (
          <>
            <ResultsDashboard
              results={results}
              errors={errors}
              onReset={handleReset}
            />
            <TemplateUploader registryData={results} />
          </>
        )}
      </main>

      {isProcessing && <ProcessingOverlay step={processingStep} />}
    </div>
  );
}

export default App;
