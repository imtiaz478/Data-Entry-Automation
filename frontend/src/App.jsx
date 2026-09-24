import { useState } from "react";

const API_URL = "http://127.0.0.1:8000";

const cellStyle = { verticalAlign: "top" };

// fetch() throws TypeError when the backend is not reachable
const describeError = (error) =>
  error instanceof TypeError
    ? "Could not connect to the backend at " + API_URL + ". " +
      "Is it running? Start it with: cd backend → venv\\Scripts\\activate → python main.py"
    : error.message;

function App() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [labelsText, setLabelsText] = useState("");
  const [keyColumns, setKeyColumns] = useState([]);
  const [sortBy, setSortBy] = useState("");
  const [sortOrder, setSortOrder] = useState("asc");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // File select → read column list for the options below
  const handleFileChange = async (event) => {
    const selected = event.target.files[0];

    setFile(selected);
    setResult(null);
    setError("");
    setPreview(null);
    setLabelsText("");
    setKeyColumns([]);
    setSortBy("");

    if (!selected) return;

    const formData = new FormData();
    formData.append("file", selected);

    try {
      const response = await fetch(`${API_URL}/upload-excel`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not read file");
      }

      setPreview(data);
      setLabelsText(data.columns.map((column) => column.name).join(", "));
      setKeyColumns(data.default_key_columns || []);
    } catch (error) {
      console.error(error);
      setError(describeError(error));
    }
  };

  // Labels = the columns the user wants in the CSV (comma separated)
  const labels = [];

  labelsText.split(",").forEach((item) => {
    const label = item.trim();

    if (label && !labels.some((l) => l.toLowerCase() === label.toLowerCase())) {
      labels.push(label);
    }
  });

  const fileColumns = preview
    ? preview.columns.map((column) => column.name.toLowerCase())
    : [];

  const newLabels = labels.filter(
    (label) => !fileColumns.includes(label.toLowerCase())
  );

  // Only columns that have data in the file can be searched with
  const isSearchable = (label) => {
    const column = preview
      ? preview.columns.find((c) => c.name.toLowerCase() === label.toLowerCase())
      : null;

    return Boolean(column) && column.empty < preview.total_rows;
  };

  const activeKeyColumns = keyColumns.filter(
    (column) => labels.includes(column) && isSearchable(column)
  );

  const toggleKeyColumn = (name) => {
    setKeyColumns((current) =>
      current.includes(name)
        ? current.filter((column) => column !== name)
        : [...current, name]
    );
  };

  // Process file
  const processFile = async () => {
    if (!file) {
      setError("Please select an Excel or CSV file first.");
      return;
    }

    setLoading(true);
    setResult(null);
    setError("");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("labels", labels.join(","));
    formData.append("key_columns", activeKeyColumns.join(","));
    formData.append("sort_by", labels.includes(sortBy) ? sortBy : "");
    formData.append("sort_order", sortOrder);

    try {
      const response = await fetch(`${API_URL}/process-excel`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Processing failed");
      }

      setResult(data);
    } catch (error) {
      console.error(error);
      setError(describeError(error));
    }

    setLoading(false);
  };

  return (
    <div
      style={{
        maxWidth: "1100px",
        margin: "40px auto",
        padding: "20px",
        fontFamily: "Arial",
      }}
    >

      {/* ========================= */}
      {/* Page Title */}
      {/* ========================= */}

      <h1>AI Data Entry Agent</h1>

      <p>
        Upload an Excel or CSV file. Cells you already filled are kept
        and checked. Empty cells are filled using web data.
      </p>


      {/* ========================= */}
      {/* Upload Section */}
      {/* ========================= */}

      <h2>Upload File</h2>

      <input
        type="file"
        accept=".xlsx,.xls,.csv"
        onChange={handleFileChange}
      />

      <br />
      <br />

      {file && (
        <p>
          <strong>Selected File:</strong> {file.name}
          {preview && (
            <> ({preview.total_rows} rows, {preview.total_columns} columns)</>
          )}
        </p>
      )}


      {/* ========================= */}
      {/* Options */}
      {/* ========================= */}

      {preview && (
        <div style={{ marginBottom: "20px" }}>

          <p>
            <strong>CSV labels (columns you want, comma separated):</strong>
          </p>

          <input
            type="text"
            value={labelsText}
            onChange={(event) => setLabelsText(event.target.value)}
            placeholder="Product, Company, Category, Price, Website"
            style={{ width: "100%", padding: "8px", boxSizing: "border-box" }}
          />

          {newLabels.length > 0 && (
            <p style={{ opacity: 0.8 }}>
              Not in your file, will be filled from the web:{" "}
              <strong>{newLabels.join(", ")}</strong>
            </p>
          )}

          <p>
            <strong>Search the web using:</strong>{" "}
            <span style={{ opacity: 0.8 }}>
              (columns that name the item, like Product and Company.
              Empty columns are filled automatically, do not tick them.)
            </span>
          </p>

          {labels.map((label) => {
            const column = preview.columns.find(
              (c) => c.name.toLowerCase() === label.toLowerCase()
            );

            const searchable = isSearchable(label);

            return (
              <label
                key={label}
                style={{ marginRight: "15px", opacity: searchable ? 1 : 0.5 }}
                title={searchable ? "" : "Empty column: will be filled, cannot be searched with"}
              >
                <input
                  type="checkbox"
                  checked={searchable && keyColumns.includes(label)}
                  disabled={!searchable}
                  onChange={() => toggleKeyColumn(label)}
                />{" "}
                {label}
                {searchable
                  ? column.empty > 0 && ` (${column.empty} empty)`
                  : " (to fill)"}
              </label>
            );
          })}

          <p>
            <strong>Sort by:</strong>{" "}
            <select
              value={sortBy}
              onChange={(event) => setSortBy(event.target.value)}
            >
              <option value="">No sorting</option>
              {labels.map((label) => (
                <option key={label} value={label}>
                  {label}
                </option>
              ))}
            </select>{" "}
            <select
              value={sortOrder}
              onChange={(event) => setSortOrder(event.target.value)}
              disabled={!sortBy}
            >
              <option value="asc">Ascending (A → Z, 1 → 9)</option>
              <option value="desc">Descending (Z → A, 9 → 1)</option>
            </select>
          </p>

        </div>
      )}

      <button
        onClick={processFile}
        disabled={loading || !preview || activeKeyColumns.length === 0}
        style={{
          padding: "10px 20px",
          cursor: loading ? "not-allowed" : "pointer",
        }}
      >
        {loading
          ? "Processing..."
          : "Fill Missing Data"}
      </button>

      {preview && activeKeyColumns.length === 0 && (
        <p style={{ color: "#b91c1c" }}>
          Tick at least one column that has data (like Product) to search with.
        </p>
      )}


      {error && (
        <p
          style={{
            marginTop: "20px",
            padding: "12px",
            border: "1px solid #b91c1c",
            borderRadius: "5px",
            color: "#ef4444",
          }}
        >
          <strong>Error:</strong> {error}
        </p>
      )}

      {result &&
        result.results.some((row) => row.status.includes("_API_KEY")) && (
          <p style={{ marginTop: "20px", color: "#f59e0b" }}>
            <strong>API key missing:</strong> create backend/.env (copy
            backend/.env.example) and add TAVILY_API_KEY and GEMINI_API_KEY,
            then restart the backend. Without keys, empty cells cannot be
            filled from the web.
          </p>
        )}


      {/* ========================= */}
      {/* Result */}
      {/* ========================= */}

      {result && (
        <div style={{ marginTop: "30px" }}>

          <h2>Processing Result</h2>

          <p>
            <strong>{result.message}</strong>
          </p>

          <p>
            <strong>Output File:</strong>{" "}
            {result.filename}
          </p>


          {/* ========================= */}
          {/* Download */}
          {/* ========================= */}

          <a
            href={`${API_URL}${result.download_url}`}
            download
            style={{
              display: "inline-block",
              marginTop: "10px",
              padding: "10px 20px",
              backgroundColor: "#2563eb",
              color: "white",
              textDecoration: "none",
              borderRadius: "5px",
            }}
          >
            Download Completed CSV
          </a>


          {/* ========================= */}
          {/* Row Results */}
          {/* ========================= */}

          {result.results && (
            <div style={{ marginTop: "30px", overflowX: "auto" }}>

              <h2>Row Processing Details</h2>

              <table
                border="1"
                cellPadding="10"
                cellSpacing="0"
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                }}
              >

                <thead>
                  <tr>
                    <th>Row</th>
                    <th>Item</th>
                    <th>Status</th>
                    <th>Filled From Web</th>
                    <th>Still Missing</th>
                    <th>Validation Issues</th>
                    <th>Source</th>
                  </tr>
                </thead>

                <tbody>

                  {result.results.map((row, index) => (

                    <tr key={index}>

                      <td style={cellStyle}>{row.row}</td>

                      <td style={cellStyle}>{row.key || "-"}</td>

                      <td style={cellStyle}>{row.status}</td>

                      <td style={cellStyle}>
                        {row.filled_fields.join(", ") || "-"}
                      </td>

                      <td style={cellStyle}>
                        {row.still_missing.join(", ") || "-"}
                      </td>

                      <td style={{ ...cellStyle, color: row.issues.length ? "#b91c1c" : undefined }}>
                        {row.issues.join("; ") || "-"}
                      </td>

                      <td style={cellStyle}>
                        {row.source_urls.length
                          ? row.source_urls.map((url, urlIndex) => (
                              <div key={url}>
                                <a
                                  href={url}
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  Open {urlIndex + 1}
                                </a>
                              </div>
                            ))
                          : "-"}
                      </td>

                    </tr>

                  ))}

                </tbody>

              </table>

            </div>
          )}

        </div>
      )}

    </div>
  );
}

export default App;
