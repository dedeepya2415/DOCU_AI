import React, { useState } from "react";
import { FiUpload, FiFileText, FiDownload, FiCheckCircle, FiLoader, FiEdit2, FiRefreshCw } from "react-icons/fi";
import axios from "axios";
import toast from "react-hot-toast";
import "./TemplateUploader.css";

const API_URL = "http://127.0.0.1:8000";

function TemplateUploader({ registryData }) {
  const [templateFile, setTemplateFile] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  
  const [previewUrl, setPreviewUrl] = useState(null);
  const [fileId, setFileId] = useState(null);
  const [mappingData, setMappingData] = useState(null);
  const [fileName, setFileName] = useState("");

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setTemplateFile(e.target.files[0]);
      setPreviewUrl(null);
      setMappingData(null);
      setFileId(null);
    }
  };

  const handleGenerate = async () => {
    if (!templateFile) {
      toast.error("Please upload a template file.");
      return;
    }

    setIsGenerating(true);
    
    const formData = new FormData();
    formData.append("template_file", templateFile);
    formData.append("registry_data", JSON.stringify(registryData));

    try {
      const response = await axios.post(`${API_URL}/generate-document`, formData, {
        responseType: 'blob', 
        timeout: 300000,
      });

      // Create preview link
      const url = window.URL.createObjectURL(new Blob([response.data], { type: response.headers['content-type'] }));
      setPreviewUrl(url);
      setFileName(`Final_${templateFile.name}`);

      // Read mapping and file ID from headers
      const mappingHeader = response.headers['x-template-mapping'];
      const fileIdHeader = response.headers['x-template-file-id'];
      const tokenUsageHeader = response.headers['x-token-usage'];
      
      if (fileIdHeader) setFileId(fileIdHeader);

      if (tokenUsageHeader) {
        try {
          const usage = JSON.parse(tokenUsageHeader);
          console.log(`🪙 AI Token Usage for Template Filling: Prompt=${usage.prompt}, Completion=${usage.completion}, Total=${usage.total}`);
        } catch (e) {
          console.error("Failed to parse token usage", e);
        }
      }

      if (mappingHeader) {
        try {
          const decoded = decodeURIComponent(mappingHeader);
          setMappingData(JSON.parse(decoded));
        } catch (e) {
          console.error("Failed to parse mapping data", e);
        }
      }

      toast.success("Initial draft generated! Please review and edit.");
    } catch (err) {
      console.error(err);
      toast.error("Failed to generate document. Please check the template.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleFieldChange = (key, value) => {
    setMappingData(prev => {
      const newData = { ...prev };
      if (newData.field_values) {
        newData.field_values[key] = value;
      }
      return newData;
    });
  };

  const handleMappingChange = (index, value) => {
    setMappingData(prev => {
      const newData = { ...prev };
      if (newData.mappings && newData.mappings[index]) {
        newData.mappings[index].replace = value;
      }
      return newData;
    });
  };

  const handleApplyEdits = async () => {
    if (!fileId || !mappingData) return;

    setIsRefreshing(true);
    const formData = new FormData();
    formData.append("file_id", fileId);
    formData.append("mapping_data", JSON.stringify(mappingData));

    try {
      const response = await axios.post(`${API_URL}/apply-template-edits`, formData, {
        responseType: 'blob',
        timeout: 120000,
      });

      // Revoke old URL to prevent memory leaks
      if (previewUrl) window.URL.revokeObjectURL(previewUrl);

      const url = window.URL.createObjectURL(new Blob([response.data], { type: response.headers['content-type'] }));
      setPreviewUrl(url);
      toast.success("Preview updated!");
    } catch (err) {
      console.error(err);
      toast.error("Failed to apply edits.");
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="template-uploader glass-card">
      <div className="template-header">
        <FiFileText size={24} color="#6366f1" />
        <h3>Generate & Edit Document</h3>
        <p>Upload your template. Our AI will draft the document, allowing you to preview and tweak it before downloading.</p>
      </div>

      {!previewUrl && (
        <>
          <div className="template-upload-area">
            <input 
              type="file" 
              accept=".pdf,.docx" 
              id="template-upload" 
              onChange={handleFileChange}
              style={{ display: 'none' }}
            />
            <label htmlFor="template-upload" className="upload-label">
              <FiUpload size={20} />
              <span>{templateFile ? templateFile.name : "Choose Template File"}</span>
            </label>
          </div>

          {templateFile && (
            <button 
              className="btn-generate" 
              onClick={handleGenerate} 
              disabled={isGenerating}
            >
              {isGenerating ? (
                <>
                  <FiLoader className="spin" /> Generating Draft...
                </>
              ) : (
                "Preview & Map Fields"
              )}
            </button>
          )}
        </>
      )}

      {previewUrl && (
        <div className="preview-container">
          <div className="preview-left">
            <h4><FiFileText /> Document Preview</h4>
            <iframe 
              src={`${previewUrl}#toolbar=0&navpanes=0&scrollbar=0`} 
              className="pdf-preview-frame"
              title="Document Preview"
            />
          </div>
          
          <div className="preview-right">
            <div className="edit-header">
              <h4><FiEdit2 /> Review & Edit Fields</h4>
              <p>Make adjustments if the AI missed or misspelled anything.</p>
            </div>
            
            <div className="edit-fields-list">
              {mappingData?.field_values && Object.entries(mappingData.field_values).map(([key, val]) => (
                <div className="edit-field" key={`field-${key}`}>
                  <label>Field {key}</label>
                  <input 
                    type="text" 
                    value={val || ""} 
                    onChange={(e) => handleFieldChange(key, e.target.value)}
                    placeholder="Leave blank if not needed..."
                  />
                </div>
              ))}

              {mappingData?.mappings && mappingData.mappings.map((mapItem, idx) => (
                <div className="edit-field" key={`map-${idx}`}>
                  <label className="context-label">Replace: "{mapItem.search}"</label>
                  <input 
                    type="text" 
                    value={mapItem.replace || ""} 
                    onChange={(e) => handleMappingChange(idx, e.target.value)}
                  />
                </div>
              ))}
            </div>

            <div className="edit-actions">
              <button 
                className="btn-secondary" 
                onClick={handleApplyEdits}
                disabled={isRefreshing}
              >
                {isRefreshing ? <FiLoader className="spin" /> : <FiRefreshCw />} Refresh Preview
              </button>
              
              <a href={previewUrl} download={fileName} className="btn-download">
                <FiDownload size={18} />
                Download Final
              </a>
            </div>

            {mappingData?.missing_fields && mappingData.missing_fields.length > 0 && (
              <div className="missing-fields-warning">
                <strong>Note:</strong> Missing data:
                <ul>
                  {mappingData.missing_fields.map((field, idx) => (
                    <li key={idx}>{field}</li>
                  ))}
                </ul>
              </div>
            )}
            
            <button 
              className="btn-text-only" 
              onClick={() => { setPreviewUrl(null); setFileId(null); }}
              style={{ marginTop: "1rem" }}
            >
              Start Over
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default TemplateUploader;
