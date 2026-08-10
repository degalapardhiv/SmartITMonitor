import { useEffect, useState } from "react";
import api from "../services/api";

export default function USBApproval() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadRequests = async () => {
    try {
      const response = await api.get("/usb/requests");
      setRequests(Array.isArray(response.data) ? response.data : []);
      setError("");
    } catch (err) {
      console.error("USB request loading failed:", err);
      setError(
        err?.response?.status === 401
          ? "Please login again."
          : "Unable to load USB requests."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRequests();

    const timer = setInterval(loadRequests, 5000);

    return () => clearInterval(timer);
  }, []);

  const decide = async (id, decision) => {
    try {
      await api.post(`/usb/requests/${id}/decision`, {
        decision,
      });

      await loadRequests();
    } catch (err) {
      console.error("USB decision failed:", err);
      setError(
        err?.response?.data?.detail ||
          "Unable to process USB decision."
      );
    }
  };

  return (
    <div style={{ padding: "24px" }}>
      <h1>USB Approval Center</h1>

      <p>
        Review USB connection requests from authorized
        managed lab computers.
      </p>

      {error && (
        <div style={{ marginBottom: "20px" }}>
          {error}
        </div>
      )}

      {loading ? (
        <p>Loading USB requests...</p>
      ) : requests.length === 0 ? (
        <p>No USB requests.</p>
      ) : (
        <div
          style={{
            display: "grid",
            gap: "16px",
          }}
        >
          {requests.map((request) => (
            <div
              key={request.id}
              style={{
                border: "1px solid #333",
                borderRadius: "12px",
                padding: "20px",
              }}
            >
              <h3>
                USB Request #{request.id}
              </h3>

              <div>
                Device ID: {request.device_id}
              </div>

              <div>
                USB ID: {request.usb_id || "N/A"}
              </div>

              <div>
                Vendor: {request.vendor || "N/A"}
              </div>

              <div>
                Product: {request.product || "N/A"}
              </div>

              <div>
                Description:{" "}
                {request.description || "N/A"}
              </div>

              <div>
                Status: <strong>{request.status}</strong>
              </div>

              <div>
                Requested:{" "}
                {request.requested_at
                  ? new Date(
                      request.requested_at
                    ).toLocaleString()
                  : "N/A"}
              </div>

              {request.reviewed_at && (
                <div>
                  Reviewed:{" "}
                  {new Date(
                    request.reviewed_at
                  ).toLocaleString()}
                </div>
              )}

              {request.reviewed_by && (
                <div>
                  Reviewed by: {request.reviewed_by}
                </div>
              )}

              {request.status === "pending" && (
                <div
                  style={{
                    display: "flex",
                    gap: "10px",
                    marginTop: "16px",
                  }}
                >
                  <button
                    onClick={() =>
                      decide(
                        request.id,
                        "approved"
                      )
                    }
                  >
                    Approve
                  </button>

                  <button
                    onClick={() =>
                      decide(
                        request.id,
                        "rejected"
                      )
                    }
                  >
                    Reject
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
