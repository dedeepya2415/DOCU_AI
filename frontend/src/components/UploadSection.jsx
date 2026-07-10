import FileDropZone from "./FileDropZone";
import {
  FiUploadCloud,
  FiArrowRight,
  FiShield,
  FiUser,
  FiHome,
} from "react-icons/fi";
import "./UploadSection.css";

const GROUP_META = {
  seller: {
    title: "Seller Documents",
    icon: <FiUser size={18} />,
    color: "#6366f1",
  },
  buyer: {
    title: "Buyer Documents",
    icon: <FiShield size={18} />,
    color: "#8b5cf6",
  },
  property: {
    title: "Property Document",
    icon: <FiHome size={18} />,
    color: "#34d399",
  },
};

function UploadSection({
  fields,
  files,
  onFileSelect,
  onFileRemove,
  onSubmit,
  allFilesUploaded,
  isProcessing,
}) {
  const uploadedCount = Object.keys(files).length;
  const totalCount = fields.length;

  const groups = {};
  fields.forEach((f) => {
    if (!groups[f.group]) groups[f.group] = [];
    groups[f.group].push(f);
  });

  return (
    <section className="upload-section" id="upload-section">
      {/* Hero area */}
      <div className="upload-hero">
        <div className="hero-icon-wrapper">
          <FiUploadCloud size={32} />
        </div>
        <h2 className="upload-title">Upload Your Documents</h2>
        <p className="upload-description">
          Upload the seller's and buyer's identity documents along with the
          property document. Our AI will extract and structure all relevant data
          automatically.
        </p>
        <div className="upload-progress-bar">
          <div className="progress-info">
            <span>
              {uploadedCount} of {totalCount} documents uploaded
            </span>
            <span className="progress-percent">
              {Math.round((uploadedCount / totalCount) * 100)}%
            </span>
          </div>
          <div className="progress-track">
            <div
              className="progress-fill"
              style={{
                width: `${(uploadedCount / totalCount) * 100}%`,
              }}
            />
          </div>
        </div>
      </div>

      {/* Grouped upload cards */}
      {Object.entries(groups).map(([groupKey, groupFields]) => {
        const meta = GROUP_META[groupKey];
        return (
          <div className="upload-group" key={groupKey}>
            <div className="group-header">
              <span
                className="group-icon"
                style={{ background: `${meta.color}20`, color: meta.color }}
              >
                {meta.icon}
              </span>
              <h3 className="group-title">{meta.title}</h3>
            </div>
            <div
              className={`group-grid ${
                groupFields.length === 1 ? "single" : ""
              }`}
            >
              {groupFields.map((field) => (
                <FileDropZone
                  key={field.key}
                  field={field}
                  file={files[field.key] || null}
                  onSelect={(file) => onFileSelect(field.key, file)}
                  onRemove={() => onFileRemove(field.key)}
                />
              ))}
            </div>
          </div>
        );
      })}

      {/* Submit button */}
      <div className="upload-actions">
        <button
          id="process-btn"
          className={`btn-process ${allFilesUploaded ? "ready" : ""}`}
          onClick={onSubmit}
          disabled={!allFilesUploaded || isProcessing}
        >
          <span>Process Documents</span>
          <FiArrowRight size={18} />
        </button>
        {!allFilesUploaded && (
          <p className="upload-hint">
            Upload all {totalCount} documents to continue
          </p>
        )}
      </div>
    </section>
  );
}

export default UploadSection;
