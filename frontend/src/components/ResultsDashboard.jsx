import {
  FiUser,
  FiShield,
  FiHome,
  FiArrowLeft,
  FiCheckCircle,
  FiAlertTriangle,
  FiCreditCard,
  FiMapPin,
  FiCalendar,
  FiHash,
  FiMaximize,
  FiDollarSign,
} from "react-icons/fi";
import "./ResultsDashboard.css";

const FIELD_ICONS = {
  name: <FiUser size={14} />,
  father_name: <FiUser size={14} />,
  dob: <FiCalendar size={14} />,
  gender: <FiUser size={14} />,
  aadhaar: <FiCreditCard size={14} />,
  pan: <FiCreditCard size={14} />,
  address: <FiMapPin size={14} />,
  property_address: <FiMapPin size={14} />,
  seller_name: <FiUser size={14} />,
  buyer_name: <FiUser size={14} />,
  registration_date: <FiCalendar size={14} />,
  survey_number: <FiHash size={14} />,
  area: <FiMaximize size={14} />,
  sale_price: <FiDollarSign size={14} />,
  document_type: <FiShield size={14} />,
  unrecognized: <FiAlertTriangle size={14} />,
};

const FIELD_LABELS = {
  name: "Full Name",
  father_name: "Father's Name",
  dob: "Date of Birth",
  gender: "Gender",
  aadhaar: "Aadhaar Number",
  pan: "PAN Number",
  address: "Address",
  document_type: "Document Type",
  property_address: "Property Address",
  seller_name: "Seller Name",
  buyer_name: "Buyer Name",
  registration_date: "Registration Date",
  survey_number: "Survey Number",
  area: "Area",
  sale_price: "Sale Price",
  raw_summary: "Summary",
  unrecognized: "Unrecognized Document",
};

function ResultsDashboard({ results, errors, onReset }) {
  const sections = [
    {
      key: "seller",
      title: "Seller Information",
      icon: <FiUser size={20} />,
      color: "#6366f1",
      data: results?.seller,
    },
    {
      key: "buyer",
      title: "Buyer Information",
      icon: <FiShield size={20} />,
      color: "#8b5cf6",
      data: results?.buyer,
    },
    {
      key: "property",
      title: "Property Details",
      icon: <FiHome size={20} />,
      color: "#34d399",
      data: results?.property,
    },
  ];

  const hasData = (data) => data && Object.keys(data).length > 0;

  return (
    <section className="results-section" id="results-section">
      {/* Success header */}
      <div className="results-header">
        <div className="results-success-icon">
          <FiCheckCircle size={28} />
        </div>
        <h2 className="results-title">Extraction Complete</h2>
        <p className="results-subtitle">
          Here is the structured data extracted from your uploaded documents.
        </p>
      </div>

      {/* Error banner if partial failure */}
      {errors && Object.keys(errors).length > 0 && (
        <div className="error-banner" id="error-banner">
          <FiAlertTriangle size={18} />
          <div>
            <strong>Some documents had issues:</strong>
            <ul className="error-list">
              {Object.entries(errors).map(([key, msg]) => (
                <li key={key}>
                  <span className="error-field">{key.replace(/_/g, " ")}</span>
                  : {msg}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Data cards */}
      <div className="results-grid">
        {sections.map((section) => (
          <div className="result-card glass-card" key={section.key}>
            <div className="result-card-header">
              <span
                className="result-card-icon"
                style={{
                  background: `${section.color}18`,
                  color: section.color,
                }}
              >
                {section.icon}
              </span>
              <h3 className="result-card-title">{section.title}</h3>
            </div>

            {hasData(section.data) ? (
              <div className="result-fields">
                {Object.entries(section.data).map(([key, value]) => {
                  if (!value && value !== 0) return null;
                  const label = FIELD_LABELS[key] || key.replace(/_/g, " ");
                  const icon = FIELD_ICONS[key] || null;
                  return (
                    <div className="result-field" key={key}>
                      <div className="field-label">
                        {icon}
                        <span>{label}</span>
                      </div>
                      <div
                        className={`field-value ${
                          key === "address" || key === "property_address"
                            ? "long"
                            : ""
                        }`}
                      >
                        {String(value)}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="result-empty">
                <p>No data extracted for this section.</p>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="results-actions">
        <button className="btn-reset" onClick={onReset} id="reset-btn">
          <FiArrowLeft size={16} />
          <span>Process New Documents</span>
        </button>
      </div>
    </section>
  );
}

export default ResultsDashboard;
