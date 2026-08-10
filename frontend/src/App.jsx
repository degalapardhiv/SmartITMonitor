import { lazy, Suspense } from "react";

import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import { useAuth } from "./context/AuthContext";

import ProtectedRoute from "./components/auth/ProtectedRoute";

import Login from "./pages/Login";
import Lab2 from "./pages/Lab2";
import USBApproval from "./pages/USBApproval";
const Dashboard = lazy(()=>import("./pages/Dashboard"));
const Devices = lazy(()=>import("./pages/Devices"));
const DeviceDetails = lazy(()=>import("./pages/DeviceDetails"));
const Departments = lazy(()=>import("./pages/Departments"));
const Alerts = lazy(()=>import("./pages/Alerts"));
const AlertCenter = lazy(()=>import("./pages/AlertCenter"));
const Reports = lazy(()=>import("./pages/Reports"));
const Settings = lazy(()=>import("./pages/Settings"));
const EmailHistory = lazy(()=>import("./pages/EmailHistory"));
const NotificationHistory = lazy(()=>import("./pages/NotificationHistory"));

function App() {
  const { isAuthenticated } = useAuth();

  return (
    <BrowserRouter>

      <Suspense fallback={
        <div className="text-white p-10">
          Loading...
        </div>
      }>

      <Routes>

        {/* Redirect Login */}
        <Route
          path="/login"
          element={
            isAuthenticated
              ? <Navigate to="/" replace />
              : <Login />
          }
        />

        {/* Dashboard */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />

        {/* Devices */}
        <Route
          path="/devices"
          element={
            <ProtectedRoute>
              <Devices />
            </ProtectedRoute>
          }
        />

        {/* Device Details */}
        <Route
          path="/devices/:id"
          element={
            <ProtectedRoute>
              <DeviceDetails />
            </ProtectedRoute>
          }
        />

        {/* Departments */}
        <Route
          path="/departments"
          element={
            <ProtectedRoute>
              <Departments />
            </ProtectedRoute>
          }
        />

        {/* Alerts */}
        <Route
          path="/alerts"
          element={
            <ProtectedRoute>
              <Alerts />
            </ProtectedRoute>
          }
        />

    
    <Route
      path="/email-history"
      element={
        <ProtectedRoute>
          <EmailHistory />
        </ProtectedRoute>
      }
    />



    <Route
      path="/alert-center"
      element={
        <ProtectedRoute>
          <AlertCenter />
        </ProtectedRoute>
      }
    />



    <Route
      path="/notification-history"
      element={
        <ProtectedRoute>
          <NotificationHistory />
        </ProtectedRoute>
      }
    />

    {/* Reports */}
        <Route
          path="/reports"
          element={
            <ProtectedRoute>
              <Reports />
            </ProtectedRoute>
          }
        />

        {/* Settings */}
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <Settings />
            </ProtectedRoute>
          }
        />

        {/* 404 */}
        <Route
          path="*"
          element={
            <Navigate
              to={isAuthenticated ? "/" : "/login"}
              replace
            />
          }
        />

      
      <Route
        path="/lab2"
        element={<Lab2 />}
      />
      <Route
        path="/usb-approval"
        element={<USBApproval />}
      />
</Routes>

      </Suspense>

    </BrowserRouter>
  );
}

export default App;
