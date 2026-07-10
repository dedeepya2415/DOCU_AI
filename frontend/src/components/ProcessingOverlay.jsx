import "./ProcessingOverlay.css";

function ProcessingOverlay({ step }) {
  return (
    <div className="processing-overlay" id="processing-overlay">
      <div className="processing-modal">
        <div className="spinner-wrapper">
          <div className="spinner-ring" />
          <div className="spinner-ring inner" />
          <div className="spinner-dot" />
        </div>
        <h3 className="processing-title">Processing Documents</h3>
        <p className="processing-step">{step}</p>
        <p className="processing-note">
          This may take a minute. Our AI is extracting text using OCR and
          structuring the data with a language model.
        </p>
        <div className="processing-bar-track">
          <div className="processing-bar-fill" />
        </div>
      </div>
    </div>
  );
}

export default ProcessingOverlay;
