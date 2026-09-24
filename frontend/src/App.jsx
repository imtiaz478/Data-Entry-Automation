import { useState } from "react";

function App() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  // Excel file select
  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
    setResult(null);
  };

  // Process Excel file
  const processFile = async () => {
    if (!file) {
      alert("Please select an Excel file first.");
      return;
    }

    setLoading(true);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/process-excel",
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Processing failed"
        );
      }

      setResult(data);

    } catch (error) {
      console.error(error);
      alert(error.message);
    }

    setLoading(false);
  };

  return (
    <div
      style={{
        maxWidth: "1000px",
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
        Upload an Excel file and automatically fill missing
        information using web data.
      </p>


      {/* ========================= */}
      {/* Upload Section */}
      {/* ========================= */}

      <h2>Upload Excel File</h2>

      <input
        type="file"
        accept=".xlsx,.xls"
        onChange={handleFileChange}
      />

      <br />
      <br />

      {file && (
        <p>
          <strong>Selected File:</strong> {file.name}
        </p>
      )}

      <button
        onClick={processFile}
        disabled={loading}
        style={{
          padding: "10px 20px",
          cursor: loading ? "not-allowed" : "pointer",
        }}
      >
        {loading
          ? "Processing..."
          : "Fill Missing Data"}
      </button>


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
            href={`http://127.0.0.1:8000${result.download_url}`}
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
            <div style={{ marginTop: "30px" }}>

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
                    <th>Product</th>
                    <th>Company</th>
                    <th>Status</th>
                    <th>URL</th>
                  </tr>
                </thead>

                <tbody>

                  {result.results.map((row, index) => (

                    <tr key={index}>

                      <td>
                        {row.row}
                      </td>

                      <td>
                        {row.product}
                      </td>

                      <td>
                        {row.company}
                      </td>

                      <td>
                        {row.status}
                      </td>

                      <td>
                        {row.url ? (
                          <a
                            href={row.url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open
                          </a>
                        ) : (
                          "-"
                        )}
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