import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import type { SessionListItem } from "../types";

export function History() {
  const navigate = useNavigate();
  const [items, setItems] = useState<SessionListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [workloadName, setWorkloadName] = useState("");
  const [status, setStatus] = useState("");
  const [sortBy, setSortBy] = useState("start_time");
  const [sortDir, setSortDir] = useState("desc");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const res = await api.listHistory({
        workloadName: workloadName || undefined,
        status: status || undefined,
        sortBy,
        sortDir,
        limit: 100,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sortBy, sortDir]);

  async function handleDelete(e: React.MouseEvent, sessionId: string) {
    e.stopPropagation();
    if (!confirm("Delete this session permanently?")) return;
    try {
      await api.deleteSession(sessionId);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Session History</div>
          <div className="page-subtitle">{total} session(s) recorded</div>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="panel" style={{ marginBottom: 14 }}>
        <div className="controls-row">
          <div className="field" style={{ flex: 2 }}>
            <label>Workload name contains</label>
            <input
              type="text"
              value={workloadName}
              onChange={(e) => setWorkloadName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && load()}
            />
          </div>
          <div className="field" style={{ width: 140 }}>
            <label>Status</label>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">All</option>
              <option value="running">Running</option>
              <option value="stopped">Stopped</option>
            </select>
          </div>
          <div className="field" style={{ width: 160 }}>
            <label>Sort by</label>
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
              <option value="start_time">Start time</option>
              <option value="runtime_seconds">Runtime</option>
              <option value="workload_name">Workload name</option>
            </select>
          </div>
          <div className="field" style={{ width: 110 }}>
            <label>Direction</label>
            <select value={sortDir} onChange={(e) => setSortDir(e.target.value)}>
              <option value="desc">Desc</option>
              <option value="asc">Asc</option>
            </select>
          </div>
          <button onClick={load}>Search</button>
        </div>
      </div>

      <div className="panel">
        <table>
          <thead>
            <tr>
              <th>Workload</th>
              <th>Status</th>
              <th>Start Time</th>
              <th>Runtime (s)</th>
              <th>Samples</th>
              <th>Energy (kWh)</th>
              <th>Cost</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.session_id} onClick={() => navigate(`/history/${item.session_id}`)}>
                <td>{item.workload_name}</td>
                <td>{item.status}</td>
                <td>{new Date(item.start_time + "Z").toLocaleString()}</td>
                <td>{item.runtime_seconds.toFixed(1)}</td>
                <td>{item.sample_count}</td>
                <td>{item.total_energy_kwh?.toExponential(2) ?? "n/a"}</td>
                <td>
                  {item.total_cost != null ? `${item.currency} ${item.total_cost.toFixed(4)}` : "n/a"}
                </td>
                <td>
                  <button className="danger" onClick={(e) => handleDelete(e, item.session_id)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td colSpan={8} style={{ textAlign: "center", color: "var(--text-faint)" }}>
                  No sessions found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
