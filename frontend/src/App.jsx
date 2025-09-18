import { useState } from "react";
import "./App.css";
import "./index.css";
import "./animations.css";
import "./spinner.css";

function App() {
  const [file, setFile] = useState(null);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setDownloadUrl(null);
      setError(null);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setError(null);
    setDownloadUrl(null);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const response = await fetch("http://127.0.0.1:5000/uploadcsv", {
        method: "POST",
        body: formData,
      });
      if (!response.ok) throw new Error("Upload failed");
      const data = await response.json();
      if (data.file_url) {
        setDownloadUrl(data.file_url);
      } else {
        throw new Error(data.error || "No file URL returned");
      }
    } catch (err) {
      setError(err.message || "Failed to upload or process file.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className='container'>
      <h1>Sheet Scan</h1>
      <p>Upload your Excel file for validation and processing</p>

      <form onSubmit={handleUpload}>
        <div className='file-upload-container'>
          <div className='file-upload-icon'>📄</div>
          <div className='file-upload-text'>
            Drag and drop your CSV file here
          </div>
          <div className='file-upload-text'>or click to browse</div>
          <input
            type='file'
            accept='.csv'
            onChange={handleFileChange}
            className='file-input'
          />
          {file && <div className='file-name'>{file.name}</div>}
        </div>

        <button
          type='submit'
          disabled={loading || !file}
          className='upload-btn'
        >
          {loading ? (
            <>
              <div className='spinner'></div>
              Processing...
            </>
          ) : (
            "Upload & Process File"
          )}
        </button>
      </form>

      {error && <div className='error-message'>{error}</div>}

      {downloadUrl && (
        <div className='download-container'>
          <p>Your file has been processed successfully!</p>
          <a href={downloadUrl} download className='download-btn'>
            <span>⬇️</span> Download Processed File
          </a>
        </div>
      )}
    </div>
  );
}

export default App;
