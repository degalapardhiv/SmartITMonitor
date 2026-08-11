import "./styles/demo-ui.css";
import { lazy, Suspense } from "react";

import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import { useAuth } from "./context/auth-context";

import ProtectedRoute from "./components/auth/ProtectedRoute";
import Layout from "./components/layout/Layout";

import Login from "./pages/Login";
import Lab2 from "./pages/Lab2";
import NetworkDiscovery from "./pages/NetworkDiscovery";
import USBApproval from "./pages/USBApproval";
import ExamMode from "./pages/ExamMode";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const Devices = lazy(() => import("./pages/Devices"));
const DeviceDetails = lazy(() => import("./pages/DeviceDetails"));
const Departments = lazy(() => import("./pages/Departments"));
const Alerts = lazy(() => import("./pages/Alerts"));
const AlertCenter = lazy(() => import("./pages/AlertCenter"));
const Reports = lazy(() => import("./pages/Reports"));
const Settings = lazy(() => import("./pages/Settings"));
const EmailHistory = lazy(() => import("./pages/EmailHistory"));
const NotificationHistory = lazy(() => import("./pages/NotificationHistory"));

function App() {
  const { isAuthenticated } = useAuth();

  return (
    <BrowserRouter>
      <Suspense fallback={<div className="text-white p-10">Loading...</div>}>

        <Routes>

          <Route
            path="/login"
            element={
              isAuthenticated
                ? <Navigate to="/" replace />
                : <Login />
            }
          />

          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/devices"
            element={
              <ProtectedRoute>
                <Devices />
              </ProtectedRoute>
            }
          />

          <Route
            path="/devices/:id"
            element={
              <ProtectedRoute>
                <DeviceDetails />
              </ProtectedRoute>
            }
          />

          <Route
            path="/departments"
            element={
              <ProtectedRoute>
                <Departments />
              </ProtectedRoute>
            }
          />

          <Route
            path="/alerts"
            element={
              <ProtectedRoute>
                <Alerts />
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
            path="/reports"
            element={
              <ProtectedRoute>
                <Reports />
              </ProtectedRoute>
            }
          />

          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <Settings />
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
            path="/notification-history"
            element={
              <ProtectedRoute>
                <NotificationHistory />
              </ProtectedRoute>
            }
          />

          <Route
            path="/network-discovery"
            element={
              <ProtectedRoute>
                <Layout>
                  <NetworkDiscovery />
                </Layout>
              </ProtectedRoute>
            }
          />

          <Route
            path="/usb-approval"
            element={
              <ProtectedRoute>
                <Layout>
                  <USBApproval />
                </Layout>
              </ProtectedRoute>
            }
          />

          <Route
            path="/exam-mode"
            element={
              <ProtectedRoute>
                <Layout>
                  <ExamMode />
                </Layout>
              </ProtectedRoute>
            }
          />

          <Route
            path="/lab2"
            element={
              <ProtectedRoute>
                <Layout>
                  <Lab2 />
                </Layout>
              </ProtectedRoute>
            }
          />

          <Route
            path="*"
            element={
              <Navigate
                to={isAuthenticated ? "/" : "/login"}
                replace
              />
            }
          />

        </Routes>

      </Suspense>
    </BrowserRouter>
  );
}

export default App;
