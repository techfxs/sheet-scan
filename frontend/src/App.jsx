import { useState } from "react";
import "./App.css";
import "./index.css";
import "./animations.css";
import "./spinner.css";

function App() {
  const [file, setFile] = useState(null);
  const [fileType, setFileType] = useState(null); // Track file type (csv or excel)
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [fileStats, setFileStats] = useState(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setDownloadUrl(null);
      setError(null);
      setFileStats(null); // Reset file statistics

      // Determine file type based on extension
      const fileName = selectedFile.name.toLowerCase();
      if (fileName.endsWith(".csv")) {
        setFileType("csv");
      } else if (fileName.endsWith(".xlsx") || fileName.endsWith(".xls")) {
        setFileType("excel");
      } else {
        setError("Unsupported file format. Please upload a CSV or Excel file.");
        setFile(null);
      }
    }
  };
  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file || !fileType) return;

    setLoading(true);
    setError(null);
    setDownloadUrl(null);
    setFileStats(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      // Select endpoint based on file type
      const endpoint =
        fileType === "csv"
          ? "http://127.0.0.1:8000/uploadcsv"
          : "http://127.0.0.1:8000/uploadwithpandas";

      const response = await fetch(endpoint, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error("Upload failed");

      if (fileType === "csv") {
        // Handle CSV response which returns a JSON with file_url and statistics
        const data = await response.json();
        if (data.file_url) {
          setDownloadUrl(data.file_url);
          // Store statistics if available
          if (data.statistics) {
            setFileStats(data.statistics);
          }
        } else {
          throw new Error(data.error || "No file URL returned");
        }
      } else {
        // Handle Excel response which returns the file directly
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        setDownloadUrl(url);

        // For Excel files, statistics are returned in headers
        const statsHeader = response.headers.get("X-Statistics");
        if (statsHeader) {
          try {
            const stats = JSON.parse(statsHeader);
            setFileStats(stats);
          } catch (err) {
            console.error("Failed to parse statistics:", err);
          }
        }
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
      <p>Upload your Excel or CSV file for validation and processing</p>

      <form onSubmit={handleUpload}>
        <div className='file-upload-container'>
          <div className='file-upload-icon'>
            {fileType === "excel" ? "📊" : "📄"}
          </div>
          <div className='file-upload-text'>Drag and drop your file here</div>
          <div className='file-upload-text'>or click to browse</div>
          <div className='supported-formats'>
            Supported formats: .csv, .xlsx, .xls
          </div>
          <input
            type='file'
            accept='.csv,.xlsx,.xls'
            onChange={handleFileChange}
            className='file-input'
          />
          {file && <div className='file-name'>{file.name}</div>}
        </div>

        <button
          type='submit'
          disabled={loading || !file}
          className={`upload-btn ${fileType ? `upload-btn-${fileType}` : ""}`}
        >
          {loading ? (
            <>
              <div className='spinner'></div>
              Processing...
            </>
          ) : (
            `Upload & Process`
          )}
        </button>
      </form>

      {error && <div className='error-message'>{error}</div>}

      {downloadUrl && (
        <div className='download-container'>
          <p>Your file has been processed successfully!</p>
          <a
            href={downloadUrl}
            download={fileType === "csv" ? "processed.csv" : "processed.xlsx"}
            className='download-btn'
          >
            <span>⬇️</span> Download Processed{" "}
            {fileType === "csv" ? "CSV" : "Excel"} File
          </a>
        </div>
      )}

      {fileStats && (
        <div className='stats-container'>
          <div className='stats-header'>
            <div className='stats-title'>File Statistics</div>
            <div className='stat-unit'>
              Processing time: {fileStats.processing_time_seconds}s
            </div>
          </div>

          <div className='stats-grid'>
            <div className='stat-card'>
              <div className='stat-label'>Total Rows</div>
              <div className='stat-value'>
                {fileStats.total_rows.toLocaleString()}
              </div>
            </div>

            <div className='stat-card'>
              <div className='stat-label'>Total Columns</div>
              <div className='stat-value'>
                {fileStats.total_columns.toLocaleString()}
              </div>
            </div>

            <div className='stat-card'>
              <div className='stat-label'>Empty Cells</div>
              <div className='stat-value'>
                {fileStats.total_empty_cells.toLocaleString()}
              </div>
            </div>

            <div className='stat-card'>
              <div className='stat-label'>Rows with Errors</div>
              <div className='stat-value'>
                {fileStats.rows_with_errors.toLocaleString()}
              </div>
            </div>
          </div>

          {/* Empty cells by column - only show if there are empty cells */}
          {fileStats.total_empty_cells > 0 && (
            <div className='empty-cells-container'>
              <div className='empty-cells-title'>Empty Cells by Column</div>
              <div className='empty-cells-grid'>
                {Object.entries(fileStats.empty_cells_by_column)
                  .filter(([_, count]) => count > 0)
                  .sort((a, b) => b[1] - a[1])
                  .map(([column, count]) => (
                    <div key={column} className='empty-cell-item'>
                      <div className='empty-cell-name' title={column}>
                        {column}
                      </div>
                      <div className='empty-cell-count'>{count}</div>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
