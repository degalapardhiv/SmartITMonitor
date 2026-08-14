import { useEffect, useState } from "react";
import AlertCharts from "../components/charts/AlertCharts";
import useWebSocket from "../hooks/useWebSocket";
import api from "../services/api";
import DeviceChart from "../components/charts/DeviceChart";
import AlertHistoryChart from "../components/AlertHistoryChart";
import ExportAlerts from "../components/ExportAlerts";
import ExportAlertsPDF from "../components/ExportAlertsPDF";
import MetricsChart from "../components/charts/MetricsChart";
import NotificationStats from "../components/cards/NotificationStats";
import LiveDevices from "../components/devices/LiveDevices";



function formatTime(value){

  if(!value){
    return "--";
  }

  const date = new Date(value);

  if(isNaN(date.getTime())){
    return "--";
  }

  return date.toLocaleTimeString();

}


function formatDateTime(value){

  if(!value){
    return "--";
  }

  const date = new Date(value);

  if(isNaN(date.getTime())){
    return "--";
  }

  return date.toLocaleString();

}


function Dashboard() {

  const [liveDevices, setLiveDevices] = useState({});

  const [liveAlert, setLiveAlert] = useState(null);

  const [liveAlerts, setLiveAlerts] = useState([]);

  const [offlineAlert, setOfflineAlert] = useState(null);

  const [history, setHistory] = useState([]);

  const [selectedDevice, setSelectedDevice] = useState(1);

  const [devices, setDevices] = useState([]);

  const [alertAnalytics,setAlertAnalytics] = useState({
    severity:[],
    types:[]
  });

  const [notificationStats,setNotificationStats] = useState({
    total:0,
    sent:0,
    failed:0,
    telegram:0,
    email:0
  });

  const [stats, setStats] = useState({
    total: 0,
    online: 0,
    offline: 0,
    alerts: 0,
    departments: 0,
    labs: 0,
  });


  async function loadNotificationStats(){

    try {

      const response = await api.get("/notifications/analytics");

      setNotificationStats(response.data);

    }
    catch(err){

      console.error(
        "Notification Stats Load Error",
        err
      );

    }

  }


  async function loadAlertAnalytics(){

    try {

      const response = await api.get("/alerts/analytics");

      setAlertAnalytics(response.data);

    }
    catch(err){

      console.error(
        "Alert Analytics Load Error",
        err
      );

    }

  }


  async function loadMetrics(){

    try{

      const response = await api.get(
        `/devices/${selectedDevice}/metrics`
      );


      setHistory(
        response.data.map(item => ({
          time: formatTime(item.created_at),
          cpu: item.cpu,
          ram: item.ram,
          disk: item.disk
        }))
      );


    }
    catch(err){

      console.error(
        "Metrics Load Error",
        err
      );

    }

  }


  async function loadDevices(){

    try{

      const response = await api.get(
        "/devices"
      );


      setDevices(
        response.data
      );


      if(response.data.length){

        setSelectedDevice(
          response.data[0].id
        );

      }

    }
    catch(err){

      console.error(
        "Device Load Error",
        err
      );

    }

  }

  async function loadDashboard() {

    try {

      const response = await api.get("/dashboard");

      setStats(response.data);

    } catch (err) {

      console.error(
        "Dashboard Error:",
        err
      );

    }

  }


  function applyLiveDevice(update){

    setLiveDevices(prev => ({
      ...prev,
      [update.id]: {
        ...(prev[update.id] || {}),
        ...update,
      },
    }));

  }


  useWebSocket((message) => {

    if (!message || !message.type) return;

    if (message.type === "alert_resolved" && message.alerts) {

      const ids = new Set(message.alerts.map(a => a.id));

      setLiveAlerts(prev =>
        prev.map(a =>
          ids.has(a.id) && a.status === "OPEN"
          ? { ...a, status: "RESOLVED", resolved_at: a.resolved_at }
          : a
        )
      );

      loadAlertAnalytics();

      loadDashboard();

      return;

    }

    if (message.type === "alert") {

      const alert = message.alert;

      if (alert) {

        setLiveAlerts(prev => {

          const exists = prev.some(a => a.id === alert.id);

          const next = exists
            ? prev.map(a => a.id === alert.id ? alert : a)
            : [alert, ...prev];

          return next.slice(0, 20);

        });

        setLiveAlert(alert);

        setTimeout(() => {
          setLiveAlert(prev => (
            prev && prev.id === alert.id ? null : prev
          ));
        }, 8000);

        loadAlertAnalytics();

        loadDashboard();

      }

      return;

    }

    if (message.type === "device_offline" && message.device) {

      applyLiveDevice({
        ...message.device,
        status: "offline",
        last_seen: new Date().toISOString()
      });

      setOfflineAlert({
        hostname: message.device.hostname
      });

      loadDashboard();

      return;

    }

    if (message.type === "device_online" && message.device) {

      applyLiveDevice({
        ...message.device,
        status: "online",
        last_seen: new Date().toISOString()
      });

      setOfflineAlert(prev =>
        prev && prev.hostname === message.device.hostname
        ? null
        : prev
      );

      loadDashboard();

      return;

    }

    if (message.type === "device_update" && message.device) {

      const update = message.device;

      applyLiveDevice(update);

      if (Number(update.id) === Number(selectedDevice)) {

        setHistory(prev => [
          ...prev.slice(-19),
          {
            time: formatTime(update.last_seen || new Date()),
            cpu: update.cpu,
            ram: update.ram,
            disk: update.disk
          }
        ]);

      }

      loadDashboard();

    }

  });


  useEffect(()=>{

    async function sync() {
      await loadNotificationStats();
    }
    sync();

    const timer=setInterval(sync,30000);


    return ()=>clearInterval(timer);


  },[]);



  useEffect(()=>{

    const timer = setInterval(()=>{

      loadAlertAnalytics();

    },30000);


    return ()=>clearInterval(timer);


  },[]);


  useEffect(() => {

    async function sync() {
      await loadDashboard();
      await loadDevices();
    }
    sync();

  }, []);


  useEffect(() => {

    async function sync() {
      if(selectedDevice){
        await loadMetrics();
      }
    }
    sync();

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDevice]);



  const selectedDeviceData =
    liveDevices[selectedDevice] ||
    devices.find(d => Number(d.id) === Number(selectedDevice)) ||
    null;


  return (
    <>
      {offlineAlert && (

        <div className="offline-alert">

          <span>
            Device Offline: {offlineAlert.hostname}
          </span>

          <button
            onClick={() => setOfflineAlert(null)}
          >
            X
          </button>

        </div>

      )}

      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">

        <div>

          <h1 className="text-[26px] font-bold tracking-tight text-white">
            Dashboard
          </h1>

          <p className="text-sm text-[var(--ds-text-2)] mt-1">
            Smart IT Monitor Overview
          </p>

        </div>

        <div className="flex flex-col gap-1">

          <label className="text-[11px] uppercase tracking-wider text-[var(--ds-text-3)] font-semibold">
            Monitoring
          </label>

          <select
            className="ui-input"
            style={{ width: 240 }}
            value={selectedDevice}
            onChange={(e)=>setSelectedDevice(Number(e.target.value))}
          >

            {
              devices.map(device => (

                <option
                  key={device.id}
                  value={device.id}
                >
                  {device.hostname}
                </option>

              ))
            }

          </select>

        </div>

      </div>


      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-4">


        <Card title="Total Devices" value={stats.total} tone="neutral"/>

        <Card title="Online Devices" value={stats.online} tone="success"/>

        <Card title="Offline Devices" value={stats.offline} tone="danger"/>

        <Card title="Alerts" value={stats.alerts} tone="warning"/>

        <Card title="Total Alert Events" value={stats.total_alerts || 0} tone="neutral"/>

        <Card title="Open Alerts" value={stats.open_alerts || 0} tone="warning"/>

        <Card title="Resolved Alerts" value={stats.resolved_alerts || 0} tone="success"/>

        <Card title="Critical Alerts" value={stats.critical_alerts || 0} tone="danger"/>

        <Card title="Departments" value={stats.departments} tone="neutral"/>

        <Card title="Labs" value={stats.labs} tone="neutral"/>


      </div>


      <div className="mt-8">

        <NotificationStats data={notificationStats} />

      </div>


      <div className="mt-8">

        <h2 className="text-lg font-bold text-white mb-4 tracking-tight">
          Live Device Monitor
        </h2>


        {selectedDeviceData ? (

          <div className="ui-card p-6">

            <div className="flex flex-wrap items-center justify-between gap-3 mb-5">

              <h3 className="text-2xl font-bold text-white">
                {selectedDeviceData.hostname}
              </h3>

              <span className={`ui-badge ${String(selectedDeviceData.status || "").toLowerCase() === "online" ? "ui-badge-success" : "ui-badge-danger"}`}>
                {selectedDeviceData.status || "unknown"}
              </span>

            </div>


            <div className="grid grid-cols-3 gap-5">

              <div className="ui-stat !p-4">
                <div className="ui-stat-label">CPU</div>
                <p className="ui-stat-value !text-2xl mt-1 text-green-400">
                  {selectedDeviceData.cpu ?? 0}%
                </p>
              </div>

              <div className="ui-stat !p-4">
                <div className="ui-stat-label">RAM</div>
                <p className="ui-stat-value !text-2xl mt-1 text-yellow-400">
                  {selectedDeviceData.ram ?? 0}%
                </p>
              </div>

              <div className="ui-stat !p-4">
                <div className="ui-stat-label">Disk</div>
                <p className="ui-stat-value !text-2xl mt-1 text-purple-400">
                  {selectedDeviceData.disk ?? 0}%
                </p>
              </div>

            </div>


            <p className="mt-5 text-sm text-[var(--ds-text-2)]">
              Last Seen: {
                formatDateTime(selectedDeviceData.last_seen)
              }
            </p>

          </div>


        ) : (

          <p className="text-[var(--ds-text-3)]">
            Waiting for live device data...
          </p>

        )}


      </div>


      <LiveDevices />


      <div className="mt-8">

        <MetricsChart data={history} />

      </div>

      <div className="mt-8">

        <DeviceChart data={history} />

      </div>


      <div className="mt-8">

        <AlertCharts
          data={alertAnalytics}
        />

      </div>


      {
        liveAlert && (

          <div className="fixed bottom-6 right-6 alert-popup alert-high text-white p-5 rounded-xl shadow-xl border-white/10" style={{ borderLeftColor: "#c22a32", borderLeftWidth: 5 }}>

            <h3 className="font-bold text-lg">
              Alert: {liveAlert.severity}
            </h3>

            <p>
              {liveAlert.message}
            </p>

            <p className="text-sm mt-2">
              Device: {liveAlert.hostname}
            </p>

            <p className="text-xs mt-1">
              {formatDateTime(liveAlert.created_at)}
            </p>

          </div>

        )
      }


      {
        liveAlerts.length > 0 && (

          <div className="mt-8">

            <h2 className="text-lg font-bold text-white mb-4 tracking-tight">
              Recent Live Alerts
            </h2>

            <div className="ui-table-wrap">

              <table className="ui-table">

                <thead>

                  <tr>

                    <th>Device</th>
                    <th>Type</th>
                    <th>Severity</th>
                    <th>Status</th>
                    <th>Time</th>

                  </tr>

                </thead>

                <tbody>

                  {
                    liveAlerts.slice(0, 10).map(alert => (

                      <tr key={alert.id}>

                        <td>
                          <p className="font-semibold text-white">{alert.hostname}</p>
                          <p className="text-xs text-[var(--ds-text-3)]">{alert.message}</p>
                        </td>

                        <td>
                          <span className="ui-badge ui-badge-neutral">{alert.alert_type}</span>
                        </td>

                        <td>
                          <span className={`ui-badge ${severityBadge(alert.severity)}`}>
                            {alert.severity}
                          </span>
                        </td>

                        <td>
                          <span className={`ui-badge ${String(alert.status || "OPEN").toUpperCase() === "RESOLVED" ? "ui-badge-success" : "ui-badge-warning"}`}>
                            {alert.status || "OPEN"}
                          </span>
                        </td>

                        <td className="whitespace-nowrap text-[var(--ds-text-2)]">
                          {formatDateTime(alert.created_at)}
                        </td>

                      </tr>

                    ))
                  }

                </tbody>

              </table>

            </div>

          </div>

        )
      }


      <div className="mt-8 flex gap-4">

        <ExportAlerts />

        <ExportAlertsPDF />

      </div>


      <div className="mt-8">

        <AlertHistoryChart />

      </div>

    </>

  );

}


function severityBadge(level) {

  const lvl = String(level || "").toUpperCase();

  if(lvl === "CRITICAL" || lvl === "HIGH")
    return "ui-badge-danger";

  if(lvl === "MEDIUM" || lvl === "WARNING")
    return "ui-badge-warning";

  return "ui-badge-success";

}


function Card({title,value,tone}) {

  const toneColor = {

    danger: "var(--ds-danger)",

    success: "var(--ds-success)",

    warning: "var(--ds-warning)",

    neutral: "var(--ds-text)",

  }[tone] || "var(--ds-text)";


  return (

    <div className="ui-stat">

      <div className="ui-stat-label">
        {title}
      </div>

      <p className="ui-stat-value" style={{ color: toneColor }}>
        {value}
      </p>

    </div>

  );

}


export default Dashboard;
