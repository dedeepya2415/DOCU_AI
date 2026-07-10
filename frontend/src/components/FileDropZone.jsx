import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import {
  FiUpload,
  FiCheckCircle,
  FiX,
  FiFile,
  FiImage,
} from "react-icons/fi";
import "./FileDropZone.css";

function FileDropZone({ field, file, onSelect, onRemove }) {
  const onDrop = useCallback(
    (acceptedFiles) => {
      if (acceptedFiles.length > 0) {
        onSelect(acceptedFiles[0]);
      }
    },
    [onSelect]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "image/*": [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"],
      "application/pdf": [".pdf"],
    },
    multiple: false,
    disabled: !!file,
  });

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const isPdf = file?.name?.endsWith(".pdf");

  return (
    <div
      className={`dropzone-card ${file ? "has-file" : ""} ${
        isDragActive ? "drag-over" : ""
      }`}
    >
      {file ? (
        <div className="dropzone-attached">
          <div className="attached-icon-wrap">
            {isPdf ? (
              <FiFile size={20} className="attached-icon" />
            ) : (
              <FiImage size={20} className="attached-icon" />
            )}
            <FiCheckCircle size={14} className="check-badge" />
          </div>
          <div className="attached-info">
            <span className="attached-name" title={file.name}>
              {file.name}
            </span>
            <span className="attached-size">{formatSize(file.size)}</span>
          </div>
          <button
            className="btn-remove"
            onClick={(e) => {
              e.stopPropagation();
              onRemove();
            }}
            title="Remove file"
          >
            <FiX size={16} />
          </button>
        </div>
      ) : (
        <div {...getRootProps()} className="dropzone-inner">
          <input {...getInputProps()} id={`upload-${field.key}`} />
          <div className="dropzone-icon">
            <FiUpload size={20} />
          </div>
          <span className="dropzone-label">{field.label}</span>
          <span className="dropzone-desc">{field.description}</span>
          <span className="dropzone-cta">
            {isDragActive ? "Drop it here!" : "Click or drag to upload"}
          </span>
        </div>
      )}
    </div>
  );
}

export default FileDropZone;
