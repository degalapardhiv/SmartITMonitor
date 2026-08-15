import { useState, useEffect, useRef } from "react";

import { useAuth } from "../context/auth-context";
import api from "../services/api";
import { getWsUrl } from "../hooks/useWebSocket";
import SettingsCenter from "./SettingsCenter";


const CIDR_RE = /^\d+\.\d+\.\d+\.\d+\/\d+$/;


function Settings() {

  const { role, username } = useAuth();

  const isViewer =
    String(role || "").toLowerCase() === "viewer";

  const isAdmin =
    String(role || "").toLowerCase() === "admin";

  const [settingsTab, setSettingsTab] = useState("center");

  const [backendStatus, setBackendStatus] = useState(
    "Checking..."
  );

  const [wsStatus, setWsStatus] = useState(
    "Checking..."
  );

  const [message, setMessage] = useState(null);

  const messageTimer = useRef(null);


  function showMessage(type, text) {

    if (messageTimer.current) {
      clearTimeout(messageTimer.current);
    }

    setMessage({ type, text });

    messageTimer.current = setTimeout(() => {
      setMessage(null);
      messageTimer.current = null;
    }, 5000);

  }


  useEffect(() => {

    return () => {
      if (messageTimer.current) {
        clearTimeout(messageTimer.current);
      }
    };

  }, []);


  async function checkBackend(){

    try{

      const response = await api.get(
        "/health"
      );

      setBackendStatus(
        response.status === 200 ? "Online" : "Offline"
      );

    }
    catch{

      setBackendStatus("Offline");

    }

  }


  useEffect(() => {

    async function sync() {
      await checkBackend();
    }

    sync();

  }, []);


  useEffect(() => {

    const socket = new WebSocket(
      getWsUrl()
    );


    socket.onopen = () => {

      setWsStatus("Active");

      socket.send("settings-check");

    };


    socket.onerror = () => {

      setWsStatus("Disconnected");

    };


    socket.onclose = () => {

      setWsStatus("Disconnected");

    };


    return () => socket.close();

  }, []);


  const [telegramEnabled, setTelegramEnabled] = useState(false);

  const [emailEnabled, setEmailEnabled] = useState(false);

  const [telegramBusy, setTelegramBusy] = useState(false);

  const [emailBusy, setEmailBusy] = useState(false);

  const [smtpConfig, setSmtpConfig] = useState({
    smtp_server:"",
    smtp_port:"",
    username:"",
    password:"",
    receiver:""
  });

  const [smtpBusy, setSmtpBusy] = useState(false);


  async function loadSmtpConfig(){

    try{

      const res = await api.get(
        "/settings/email/config"
      );

      const data = res.data;


      if(data.configured){

        setSmtpConfig({
          smtp_server:data.smtp_server || "",
          smtp_port:data.smtp_port || "",
          username:data.username || "",
          password:"",
          receiver:data.receiver || ""
        });

      }
      else{

        setSmtpConfig({
          smtp_server:"",
          smtp_port:"",
          username:"",
          password:"",
          receiver:""
        });

      }

    }
    catch(err){

      console.error(err);

      showMessage("error", "Failed to load SMTP configuration");

    }

  }



  useEffect(() => {

    async function sync() {
      await loadSmtpConfig();
    }

    sync();

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);



  function updateSmtp(field,value){

    setSmtpConfig({

      ...smtpConfig,

      [field]:value

    });

  }




  async function saveSmtpConfig(){

    setSmtpBusy(true);

    try{

      const body = {
        smtp_server: smtpConfig.smtp_server,
        smtp_port: Number(smtpConfig.smtp_port) || 0,
        username: smtpConfig.username,
        receiver: smtpConfig.receiver,
        password: smtpConfig.password
      };

      await api.post(
        "/settings/email/config",
        body
      );

      showMessage("success", "SMTP settings saved");

    }
    catch(err){

      console.error(err);

      showMessage("error", "Failed to save SMTP settings");

    }
    finally{

      setSmtpBusy(false);

    }

  }


  async function resetSmtpConfig(){

    if(!window.confirm("Reset SMTP configuration?")) return;

    setSmtpBusy(true);

    try{

      await api.delete("/settings/email/config");

      await loadSmtpConfig();

      showMessage("success", "SMTP settings reset");

    }
    catch(err){

      console.error(err);

      showMessage("error", "Failed to reset SMTP settings");

    }
    finally{

      setSmtpBusy(false);

    }

  }




  async function loadEmailStatus(){

    try{

      const res = await api.get(
        "/settings/email"
      );

      const data = res.data;

      setEmailEnabled(
        Boolean(data.email_enabled)
      );

    }
    catch(err){

      console.error(err);

      showMessage("error", "Failed to load email settings");

    }

  }



  useEffect(() => {

    async function sync() {
      await loadEmailStatus();
    }

    sync();

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);



  async function toggleEmail(){

    if (emailBusy) return;

    const value = !emailEnabled;

    setEmailBusy(true);

    try{

      await api.post(
        "/settings/email",
        null,
        { params: { enabled: value } }
      );

      setEmailEnabled(value);

      showMessage("success", "Email alerts updated");

    }
    catch(err){

      console.error(err);

      showMessage("error", "Failed to update email alerts");

    }
    finally{

      setEmailBusy(false);

    }

  }




  async function loadTelegramStatus(){

    try{

      const res = await api.get("/settings/telegram");

      const data = res.data;

      setTelegramEnabled(
        Boolean(data.telegram_enabled)
      );

    }
    catch(err){

      console.error(err);

      showMessage("error", "Failed to load Telegram settings");

    }

  }


  useEffect(() => {

    async function sync() {
      await loadTelegramStatus();
    }

    sync();

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);


  async function toggleTelegram(){

    if (telegramBusy) return;

    const value = !telegramEnabled;

    setTelegramBusy(true);

    try{

      await api.post(
        "/settings/telegram",
        null,
        { params: { enabled: value } }
      );

      setTelegramEnabled(value);

      showMessage("success", "Telegram alerts updated");

    }
    catch(err){

      console.error(err);

      showMessage("error", "Failed to update Telegram alerts");

    }
    finally{

      setTelegramBusy(false);

    }

  }



  const [notifications, setNotifications] = useState(
    () => localStorage.getItem("notificationsEnabled") !== "false"
  );

  const [darkMode, setDarkMode] = useState(
    () => localStorage.getItem("darkMode") !== "false"
  );


  useEffect(() => {

    document.body.classList.toggle("dark", darkMode);

    document.body.dataset.theme = darkMode ? "dark" : "light";

  }, [darkMode]);


  function savePreferences(){

    localStorage.setItem("notificationsEnabled", String(notifications));
    localStorage.setItem("darkMode", String(darkMode));

    showMessage("success", "Preferences saved");

  }


  const [passwordForm, setPasswordForm] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: ""
  });

  const [passwordBusy, setPasswordBusy] = useState(false);


  async function changePassword(e){

    e.preventDefault();

    const { currentPassword, newPassword, confirmPassword } = passwordForm;

    if (!currentPassword) {

      showMessage("error", "Current password is required");
      return;

    }

    if (newPassword.length < 8) {

      showMessage("error", "New password must be at least 8 characters");
      return;

    }

    if (newPassword !== confirmPassword) {

      showMessage("error", "New password and confirmation do not match");
      return;

    }

    setPasswordBusy(true);

    try{

      const formData = new FormData();
      formData.append("current_password", currentPassword);
      formData.append("new_password", newPassword);

      await api.post("/change-password", formData, {
        headers: { "Content-Type": undefined }
      });

      setPasswordForm({
        currentPassword: "",
        newPassword: "",
        confirmPassword: ""
      });

      showMessage("success", "Password changed successfully");

    }
    catch(err){

      console.error(err);

      const detail =
        err?.response?.data?.detail ||
        "Failed to change password";

      showMessage("error", detail);

    }
    finally{

      setPasswordBusy(false);

    }

  }


  async function testEmail(){

    setSmtpBusy(true);

    try{

      await api.post("/settings/test-email");

      showMessage("success", "Email test sent");

    }
    catch(err){

      console.error(err);

      showMessage("error",
        err?.response?.data?.detail || "Email test failed"
      );

    }
    finally{

      setSmtpBusy(false);

    }

  }


  async function testTelegram(){

    try{

      await api.post("/settings/test-telegram");

      showMessage("success", "Telegram test sent");

    }
    catch(err){

      console.error(err);

      showMessage("error", "Failed to send Telegram test");

    }

  }


  const [departments, setDepartments] = useState([]);

  const [newDepartment, setNewDepartment] = useState("");

  const [editingDept, setEditingDept] = useState(null);

  const [departmentsBusy, setDepartmentsBusy] = useState(false);


  async function loadDepartments(){

    try{

      const res = await api.get("/departments");

      setDepartments(res.data || []);

    }
    catch(err){

      console.error(err);

      showMessage("error", "Failed to load departments");

    }

  }


  async function addDepartment(){

    if(!newDepartment.trim()) return;

    setDepartmentsBusy(true);

    try{

      await api.post("/departments", { name: newDepartment.trim() });

      setNewDepartment("");

      await loadDepartments();

      showMessage("success", "Department added");

    }
    catch(err){

      console.error(err);

      showMessage("error",
        err?.response?.data?.detail || "Failed to add department"
      );

    }
    finally{

      setDepartmentsBusy(false);

    }

  }


  async function saveDepartment(id){

    if(!editingDept || !editingDept.name.trim()) return;

    setDepartmentsBusy(true);

    try{

      await api.put(`/departments/${id}`, { name: editingDept.name.trim() });

      setEditingDept(null);

      await loadDepartments();

      showMessage("success", "Department updated");

    }
    catch(err){

      console.error(err);

      showMessage("error",
        err?.response?.data?.detail || "Failed to update department"
      );

    }
    finally{

      setDepartmentsBusy(false);

    }

  }


  async function deleteDepartment(id){

    if(!window.confirm("Delete this department?")) return;

    setDepartmentsBusy(true);

    try{

      await api.delete(`/departments/${id}`);

      await loadDepartments();

      showMessage("success", "Department deleted");

    }
    catch(err){

      console.error(err);

      showMessage("error",
        err?.response?.data?.detail || "Failed to delete department"
      );

    }
    finally{

      setDepartmentsBusy(false);

    }

  }


  const [monitorSettings, setMonitorSettings] = useState({
    cpu_threshold:"",
    ram_threshold:"",
    disk_threshold:"",
    alert_cooldown_minutes:""
  });

  const [scanRanges, setScanRanges] = useState([]);

  const [newRange, setNewRange] = useState("");

  const [monitorBusy, setMonitorBusy] = useState(false);


  async function loadMonitorSettings(){

    try{

      const res = await api.get("/settings/monitor");

      const data = res.data || {};

      setMonitorSettings({
        cpu_threshold: data.cpu_threshold ?? "",
        ram_threshold: data.ram_threshold ?? "",
        disk_threshold: data.disk_threshold ?? "",
        alert_cooldown_minutes: data.alert_cooldown_minutes ?? ""
      });

      setScanRanges(data.scan_ranges || []);

    }
    catch(err){

      console.error(err);

      showMessage("error", "Failed to load monitoring settings");

    }

  }


  function monitorPayload(){

    return {
      cpu_threshold: Number(monitorSettings.cpu_threshold) || 0,
      ram_threshold: Number(monitorSettings.ram_threshold) || 0,
      disk_threshold: Number(monitorSettings.disk_threshold) || 0,
      alert_cooldown_minutes: Number(monitorSettings.alert_cooldown_minutes) || 0,
      scan_ranges: scanRanges
    };

  }


  async function saveThresholds(){

    setMonitorBusy(true);

    try{

      await api.put("/settings/monitor", monitorPayload());

      showMessage("success", "Alert thresholds saved");

    }
    catch(err){

      console.error(err);

      showMessage("error",
        err?.response?.data?.detail || "Failed to save alert thresholds"
      );

    }
    finally{

      setMonitorBusy(false);

    }

  }


  function addRange(){

    const range = newRange.trim();

    if(!CIDR_RE.test(range)){

      showMessage("error", "Invalid CIDR range");

      return;

    }

    setScanRanges([...scanRanges, range]);

    setNewRange("");

  }


  function removeRange(index){

    setScanRanges(
      scanRanges.filter((_, i) => i !== index)
    );

  }


  async function saveRanges(){

    setMonitorBusy(true);

    try{

      await api.put("/settings/monitor", monitorPayload());

      showMessage("success", "Scan ranges saved");

    }
    catch(err){

      console.error(err);

      showMessage("error",
        err?.response?.data?.detail || "Failed to save scan ranges"
      );

    }
    finally{

      setMonitorBusy(false);

    }

  }


  useEffect(() => {

    if(!isAdmin) return;

    async function sync() {
      await loadDepartments();
      await loadMonitorSettings();
    }

    sync();

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin]);


  return (
    <>
      <div className="ui-page-header !mb-6">

        <div>

          <h1 className="ui-page-title">
            Settings
          </h1>

          <p className="ui-page-subtitle">
            Configure Smart IT Monitor
          </p>

        </div>

      </div>

      {message && (
        <div
          className={
            message.type === "error"
            ? "mb-6 rounded-lg border border-red-600/40 bg-red-600/15 p-4 text-[#e6797e]"
            : "mb-6 rounded-lg border border-green-500/30 bg-green-500/10 p-4 text-[#46d369]"
          }
        >
          {message.text}
        </div>
      )}

      <div className="ui-tabs !mb-8">
        <button
          type="button"
          onClick={() => setSettingsTab("center")}
          className={`ui-tab ${settingsTab === "center" ? "ui-tab-active" : ""}`}
        >
          Configuration Center
        </button>
        <button
          type="button"
          onClick={() => setSettingsTab("advanced")}
          className={`ui-tab ${settingsTab === "advanced" ? "ui-tab-active" : ""}`}
        >
          Advanced
        </button>
      </div>

      {settingsTab === "center" && (
        <SettingsCenter showMessage={showMessage} />
      )}

      {settingsTab === "advanced" && (
      <>
      <div className="grid lg:grid-cols-2 gap-8">

        {/* User Profile */}

        <div className="ui-card p-6">

          <h2 className="text-lg font-bold text-white mb-5 tracking-tight">
            User Profile
          </h2>

          <div className="space-y-5">

            <div>

              <label className="block text-gray-400 mb-2">
                Username
              </label>

              <input
                type="text"
                value={username || "admin"}
                readOnly
                className="w-full bg-slate-700 rounded-lg p-3"
              />

            </div>

            <div>

              <label className="block text-gray-400 mb-2">
                Role
              </label>

              <input
                type="text"
                value={role || "Guest"}
                readOnly
                className="w-full bg-slate-700 rounded-lg p-3"
              />

            </div>

            {isViewer && (
              <p className="text-yellow-400 text-sm">
                You have viewer access. Administrative actions are hidden.
              </p>
            )}

          </div>

        </div>


        {/* API Configuration */}

        <div className="ui-card p-6">

          <h2 className="text-lg font-bold text-white mb-5 tracking-tight">
            API Configuration
          </h2>

          <div className="space-y-5">

            <div>

              <label className="block text-gray-400 mb-2">
                Backend API URL
              </label>

              <input
                type="text"
                value="/api"
                readOnly
                className="w-full bg-slate-700 rounded-lg p-3"
              />

            </div>

            <p className="text-gray-400 text-sm">
              The API URL is fixed by the application deployment / reverse proxy.
            </p>

          </div>

        </div>

      </div>
      <div className="grid lg:grid-cols-2 gap-8 mt-8">

        {/* Notification Settings */}

        <div className="ui-card p-6">

          <h2 className="text-lg font-bold text-white mb-5 tracking-tight">
            Notification Settings
          </h2>

          <div className="space-y-6">

            <div className="flex justify-between items-center">

              <div>

                <h3 className="font-semibold">
                  Enable Notifications
                </h3>

                <p className="text-gray-400 text-sm">
                  Receive alert notifications
                </p>

              </div>

              <input
                type="checkbox"
                checked={notifications}
                onChange={() =>
                  setNotifications(!notifications)
                }
                className="w-5 h-5"
              />

            </div>

            <div className="flex justify-between items-center">

              <div>

                <h3 className="font-semibold">
                  Telegram Alerts
                </h3>

                <p className="text-gray-400 text-sm">
                  Receive Telegram notifications
                </p>

              </div>


              <input
                type="checkbox"
                checked={telegramEnabled}
                onChange={toggleTelegram}
                disabled={telegramBusy}
                className="w-5 h-5"
              />

            </div>


            <div className="flex justify-between items-center">

              <div>

                <h3 className="font-semibold">
                  Email Alerts
                </h3>

                <p className="text-gray-400 text-sm">
                  Send alerts through email
                </p>

              </div>


              <input
                type="checkbox"
                checked={emailEnabled}
                onChange={toggleEmail}
                disabled={emailBusy}
                className="w-5 h-5"
              />

            </div>


            <div className="flex justify-between items-center">

              <div>

                <h3 className="font-semibold">
                  Dark Mode
                </h3>

                <p className="text-gray-400 text-sm">
                  Enable dark interface
                </p>

              </div>

              <input
                type="checkbox"
                checked={darkMode}
                onChange={() =>
                  setDarkMode(!darkMode)
                }
                className="w-5 h-5"
              />

            </div>

            <button
              onClick={savePreferences}
              className="bg-cyan-600 hover:bg-cyan-700 px-6 py-3 rounded-lg"
            >
              Save Preferences
            </button>

          </div>

        </div>




        {/* SMTP Email Configuration */}

        <div className="ui-card p-6">

          <h2 className="text-lg font-bold text-white mb-5 tracking-tight">
            SMTP Email Configuration
          </h2>


          <div className="space-y-4">


            <input
              placeholder="SMTP Server"
              value={smtpConfig.smtp_server}
              onChange={(e)=>updateSmtp("smtp_server",e.target.value)}
              className="w-full bg-slate-700 rounded-lg p-3"
            />


            <input
              placeholder="SMTP Port"
              value={smtpConfig.smtp_port}
              onChange={(e)=>updateSmtp("smtp_port",e.target.value)}
              className="w-full bg-slate-700 rounded-lg p-3"
            />


            <input
              placeholder="Email Username"
              value={smtpConfig.username}
              onChange={(e)=>updateSmtp("username",e.target.value)}
              className="w-full bg-slate-700 rounded-lg p-3"
            />


            <input
              placeholder="App Password"
              type="password"
              value={smtpConfig.password}
              onChange={(e)=>updateSmtp("password",e.target.value)}
              className="w-full bg-slate-700 rounded-lg p-3"
            />


            <input
              placeholder="Receiver Email"
              value={smtpConfig.receiver}
              onChange={(e)=>updateSmtp("receiver",e.target.value)}
              className="w-full bg-slate-700 rounded-lg p-3"
            />


            <div className="flex gap-3">

              <button
                onClick={saveSmtpConfig}
                disabled={smtpBusy || !isAdmin}
                className="bg-cyan-600 hover:bg-cyan-700 px-6 py-3 rounded-lg disabled:opacity-50"
              >
                {smtpBusy ? "Saving..." : "Save SMTP Settings"}
              </button>


              <button
                onClick={testEmail}
                disabled={smtpBusy}
                className="bg-green-600 hover:bg-green-700 px-6 py-3 rounded-lg disabled:opacity-50"
              >
                Test Email
              </button>


              {isAdmin && (
                <button
                  onClick={resetSmtpConfig}
                  disabled={smtpBusy}
                  className="bg-red-600 hover:bg-red-700 px-6 py-3 rounded-lg disabled:opacity-50"
                >
                  Reset SMTP Settings
                </button>
              )}

            </div>


          </div>

        </div>


        {/* System Status */}

        <div className="ui-card p-6">

          <h2 className="text-lg font-bold text-white mb-5 tracking-tight">
            System Status
          </h2>

          <div className="space-y-5">

            <div className="flex justify-between items-center">

              <span className="text-[var(--ds-text-2)]">Backend API</span>

              <span
                className={
                  backendStatus === "Online"
                    ? "ui-badge ui-badge-success"
                    : "ui-badge ui-badge-danger"
                }
              >
                {backendStatus}
              </span>

            </div>

            <div className="flex justify-between items-center">

              <span className="text-[var(--ds-text-2)]">Database</span>

              <span className="ui-badge ui-badge-success">
                PostgreSQL Online
              </span>

            </div>

            <div className="flex justify-between items-center">

              <span className="text-[var(--ds-text-2)]">WebSocket</span>

              <span
                className={
                  wsStatus === "Active"
                    ? "ui-badge ui-badge-success"
                    : "ui-badge ui-badge-danger"
                }
              >
                {wsStatus}
              </span>

            </div>

            <div className="flex justify-between">

              <span>Frontend</span>

              <span className="text-green-400 font-bold">
                React + Vite
              </span>

            </div>

            <div className="flex gap-3 pt-2">

              <button
                onClick={testTelegram}
                className="bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-lg"
              >
                Test Telegram
              </button>

            </div>

          </div>

        </div>

      </div>
      <div className="grid lg:grid-cols-2 gap-8 mt-8">

        {/* Change Password */}

        <div className="ui-card p-6">

          <h2 className="text-lg font-bold text-white mb-5 tracking-tight">
            Change Password
          </h2>

          <form className="space-y-5" onSubmit={changePassword}>

            <div>

              <label className="block text-gray-400 mb-2">
                Current Password
              </label>

              <input
                type="password"
                placeholder="Current Password"
                value={passwordForm.currentPassword}
                onChange={(e)=>setPasswordForm({
                  ...passwordForm,
                  currentPassword:e.target.value
                })}
                className="w-full bg-slate-700 rounded-lg p-3"
              />

            </div>

            <div>

              <label className="block text-gray-400 mb-2">
                New Password
              </label>

              <input
                type="password"
                placeholder="New Password"
                value={passwordForm.newPassword}
                onChange={(e)=>setPasswordForm({
                  ...passwordForm,
                  newPassword:e.target.value
                })}
                className="w-full bg-slate-700 rounded-lg p-3"
              />

            </div>

            <div>

              <label className="block text-gray-400 mb-2">
                Confirm Password
              </label>

              <input
                type="password"
                placeholder="Confirm Password"
                value={passwordForm.confirmPassword}
                onChange={(e)=>setPasswordForm({
                  ...passwordForm,
                  confirmPassword:e.target.value
                })}
                className="w-full bg-slate-700 rounded-lg p-3"
              />

            </div>

            <button
              type="submit"
              disabled={passwordBusy}
              className="bg-red-600 hover:bg-red-700 px-6 py-3 rounded-lg disabled:opacity-50"
            >
              {passwordBusy ? "Updating..." : "Update Password"}
            </button>

          </form>

        </div>


        {/* Application Information */}

        <div className="ui-card p-6">

          <h2 className="text-lg font-bold text-white mb-5 tracking-tight">
            Application Information
          </h2>

          <div className="space-y-4">

            <div className="flex justify-between">

              <span>Application</span>

              <span className="font-semibold">
                Smart IT Monitor
              </span>

            </div>

            <div className="flex justify-between">

              <span>Version</span>

              <span className="text-cyan-400 font-bold">
                2.0.0
              </span>

            </div>

            <div className="flex justify-between">

              <span>Frontend</span>

              <span>
                React + Vite
              </span>

            </div>

            <div className="flex justify-between">

              <span>Backend</span>

              <span>
                FastAPI
              </span>

            </div>

            <div className="flex justify-between">

              <span>Database</span>

              <span>
                PostgreSQL
              </span>

            </div>

            <div className="flex justify-between">

              <span>Authentication</span>

              <span>
                JWT
              </span>

            </div>

            <div className="flex justify-between">

              <span>Monitoring</span>

              <span>
                Real-Time WebSocket
              </span>

            </div>

            <hr className="border-slate-700 my-4" />

            <div className="text-center">

              <p className="text-gray-400">
                Developed using
              </p>

              <p className="text-cyan-400 font-bold mt-2">
                React • FastAPI • PostgreSQL
              </p>

            </div>

          </div>

        </div>


        {isAdmin && (

          <div className="ui-card p-6">

            <h2 className="text-lg font-bold text-white mb-5 tracking-tight">
              Departments
            </h2>

            <div className="space-y-3 mb-5">

              {departments.map((dept) => (

                <div
                  key={dept.id}
                  className="flex gap-3 items-center"
                >

                  {editingDept && editingDept.id === dept.id ? (

                    <input
                      value={editingDept.name}
                      onChange={(e)=>setEditingDept({
                        ...editingDept,
                        name:e.target.value
                      })}
                      className="flex-1 bg-slate-700 rounded-lg p-3"
                    />

                  ) : (

                    <span className="flex-1 text-gray-300">
                      {dept.name}
                    </span>

                  )}

                  {editingDept && editingDept.id === dept.id ? (

                    <button
                      onClick={()=>saveDepartment(dept.id)}
                      disabled={departmentsBusy}
                      className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg disabled:opacity-50"
                    >
                      Save
                    </button>

                  ) : (

                    <button
                      onClick={()=>setEditingDept({
                        id: dept.id,
                        name: dept.name
                      })}
                      className="bg-yellow-600 hover:bg-yellow-700 px-4 py-2 rounded-lg"
                    >
                      Edit
                    </button>

                  )}

                  <button
                    onClick={()=>deleteDepartment(dept.id)}
                    disabled={departmentsBusy}
                    className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded-lg disabled:opacity-50"
                  >
                    Delete
                  </button>

                </div>

              ))}

            </div>

            <div className="flex gap-3">

              <input
                placeholder="New department name"
                value={newDepartment}
                onChange={(e)=>setNewDepartment(e.target.value)}
                className="flex-1 bg-slate-700 rounded-lg p-3"
              />

              <button
                onClick={addDepartment}
                disabled={departmentsBusy}
                className="bg-cyan-600 hover:bg-cyan-700 px-6 py-3 rounded-lg disabled:opacity-50"
              >
                Add Department
              </button>

            </div>

          </div>

        )}



        {isAdmin && (

          <div className="ui-card p-6">

            <h2 className="text-lg font-bold text-white mb-5 tracking-tight">
              Alert Thresholds
            </h2>

            <div className="space-y-4">

              <div>

                <label className="block text-gray-400 mb-2">
                  CPU Threshold (%)
                </label>

                <input
                  type="number"
                  value={monitorSettings.cpu_threshold}
                  onChange={(e)=>setMonitorSettings({
                    ...monitorSettings,
                    cpu_threshold:e.target.value
                  })}
                  className="w-full bg-slate-700 rounded-lg p-3"
                />

              </div>


              <div>

                <label className="block text-gray-400 mb-2">
                  RAM Threshold (%)
                </label>

                <input
                  type="number"
                  value={monitorSettings.ram_threshold}
                  onChange={(e)=>setMonitorSettings({
                    ...monitorSettings,
                    ram_threshold:e.target.value
                  })}
                  className="w-full bg-slate-700 rounded-lg p-3"
                />

              </div>


              <div>

                <label className="block text-gray-400 mb-2">
                  Disk Threshold (%)
                </label>

                <input
                  type="number"
                  value={monitorSettings.disk_threshold}
                  onChange={(e)=>setMonitorSettings({
                    ...monitorSettings,
                    disk_threshold:e.target.value
                  })}
                  className="w-full bg-slate-700 rounded-lg p-3"
                />

              </div>


              <div>

                <label className="block text-gray-400 mb-2">
                  Alert Cooldown (minutes)
                </label>

                <input
                  type="number"
                  value={monitorSettings.alert_cooldown_minutes}
                  onChange={(e)=>setMonitorSettings({
                    ...monitorSettings,
                    alert_cooldown_minutes:e.target.value
                  })}
                  className="w-full bg-slate-700 rounded-lg p-3"
                />

              </div>


              <button
                onClick={saveThresholds}
                disabled={monitorBusy}
                className="bg-cyan-600 hover:bg-cyan-700 px-6 py-3 rounded-lg disabled:opacity-50"
              >
                {monitorBusy ? "Saving..." : "Save Thresholds"}
              </button>

            </div>

          </div>

        )}



        {isAdmin && (

          <div className="ui-card p-6">

            <h2 className="text-lg font-bold text-white mb-5 tracking-tight">
              Network Scan Ranges
            </h2>

            <div className="space-y-3 mb-5">

              {scanRanges.map((range,index) => (

                <div
                  key={range}
                  className="flex gap-3 items-center"
                >

                  <span className="flex-1 text-gray-300">
                    {range}
                  </span>

                  <button
                    onClick={()=>removeRange(index)}
                    className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded-lg"
                  >
                    Remove
                  </button>

                </div>

              ))}

            </div>


            <div className="flex gap-3 mb-5">

              <input
                placeholder="e.g. 192.168.1.0/24"
                value={newRange}
                onChange={(e)=>setNewRange(e.target.value)}
                className="flex-1 bg-slate-700 rounded-lg p-3"
              />

              <button
                onClick={addRange}
                className="bg-cyan-600 hover:bg-cyan-700 px-6 py-3 rounded-lg"
              >
                Add Range
              </button>

            </div>


            <button
              onClick={saveRanges}
              disabled={monitorBusy}
              className="bg-cyan-600 hover:bg-cyan-700 px-6 py-3 rounded-lg disabled:opacity-50"
            >
              {monitorBusy ? "Saving..." : "Save Ranges"}
            </button>

          </div>

        )}

      </div>
      <div className="grid lg:grid-cols-2 gap-8 mt-8">

        {/* Storage & Statistics */}

        <div className="ui-card p-6">

          <h2 className="text-lg font-bold text-white mb-5 tracking-tight">
            System Statistics
          </h2>

          <div className="space-y-5">

            <div>

              <div className="flex justify-between mb-2">

                <span>Database Storage</span>

                <span className="font-bold">
                  68%
                </span>

              </div>

              <div className="w-full bg-slate-700 rounded-full h-3">

                <div
                  className="bg-blue-500 h-3 rounded-full"
                  style={{ width: "68%" }}
                />

              </div>

            </div>

            <div>

              <div className="flex justify-between mb-2">

                <span>CPU Usage</span>

                <span className="font-bold">
                  34%
                </span>

              </div>

              <div className="w-full bg-slate-700 rounded-full h-3">

                <div
                  className="bg-green-500 h-3 rounded-full"
                  style={{ width: "34%" }}
                />

              </div>

            </div>

            <div>

              <div className="flex justify-between mb-2">

                <span>Memory Usage</span>

                <span className="font-bold">
                  52%
                </span>

              </div>

              <div className="w-full bg-slate-700 rounded-full h-3">

                <div
                  className="bg-yellow-500 h-3 rounded-full"
                  style={{ width: "52%" }}
                />

              </div>

            </div>

            <div>

              <div className="flex justify-between mb-2">

                <span>Disk Usage</span>

                <span className="font-bold">
                  71%
                </span>

              </div>

              <div className="w-full bg-slate-700 rounded-full h-3">

                <div
                  className="bg-red-500 h-3 rounded-full"
                  style={{ width: "71%" }}
                />

              </div>

            </div>

          </div>

        </div>

      </div>
      </>
      )}
    </>

  );

}

export default Settings;
