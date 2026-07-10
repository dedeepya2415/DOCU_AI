import { FiFileText } from "react-icons/fi";
import "./Header.css";

function Header() {
  return (
    <header className="header" id="header">
      <div className="header-inner">
        <div className="header-brand">
          <div className="header-logo">
            <FiFileText size={22} />
          </div>
          <div>
            <h1 className="header-title">DOCU-AI</h1>
            <p className="header-subtitle">Smart Document Processing</p>
          </div>
        </div>
        <div className="header-badge">
          <span className="badge-dot" />
          <span>AI-Powered</span>
        </div>
      </div>
    </header>
  );
}

export default Header;
