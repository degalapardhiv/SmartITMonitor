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
const Cctv = lazy(() => import("./pages/Cctv"));
const OsDeployment = lazy(() => import("./pages/OsDeployment"));
const EndpointActivity = lazy(() => import("./pages/EndpointActivity"));
const SoftwareDeployment = lazy(() => import("./pages/SoftwareDeployment"));
const NetworkDiscovery = lazy(() => import("./pages/NetworkDiscovery"));
const USBApproval = lazy(() => import("./pages/USBApproval"));
const ExamMode = lazy(() => import("./pages/ExamMode"));
const Lab2 = lazy(() => import("./pages/Lab2"));
const Threats = lazy(() => import("./pages/Threats"));
const WebAccessControl = lazy(() => import("./pages/WebAccessControl"));

function App() {
  const { isAuthenticated } = useAuth();

  const shell = (page) => <Layout>{page}</Layout>;

  return (
    <BrowserRouter>
      <Suspense fallback={<div className="text-white p-10">Loading...</div>}>
        <Routes>
          <Route
            path="/login"
            element={
              isAuthenticated ? (
                <Navigate to="/" replace />
              ) : (
                <Login />
              )
            }
          />

          <Route
            path="/"
            element={
              <ProtectedRoute>
                {shell(<Dashboard />)}
              </ProtectedRoute>
            }
          />

          <Route
            path="/devices"
            element={
              <ProtectedRoute>
                {shell(<Devices />)}
              </ProtectedRoute>
            }
          />

          <Route
            path="/devices/:id"
            element={
              <ProtectedRoute>
                {shell(<DeviceDetails />)}
              </ProtectedRoute>
            }
          />

          <Route
            path="/departments"
            element={
              <ProtectedRoute>
                {shell(<Departments />)}
              </ProtectedRoute>
            }
          />

          <Route
            path="/alerts"
            element={
              <ProtectedRoute>
                {shell(<Alerts />)}
              </ProtectedRoute>
            }
          />

          <Route
            path="/alert-center"
            element={
              <ProtectedRoute>
                {shell(<AlertCenter />)}
              </ProtectedRoute>
            }
          />

          <Route
            path="/reports"
            element={
              <ProtectedRoute>
                {shell(<Reports />)}
              </ProtectedRoute>
            }
          />

          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                {shell(<Settings />)}
              </ProtectedRoute>
            }
          />

          <Route
            path="/email-history"
            element={
              <ProtectedRoute>
                {shell(<EmailHistory />)}
              </ProtectedRoute>
            }
          />

          <Route
            path="/notification-history"
            element={
              <ProtectedRoute>
                {shell(<NotificationHistory />)}
              </ProtectedRoute>
            }
          />

          <Route
            path="/network-discovery"
            element={
              <ProtectedRoute>
                {shell(<NetworkDiscovery />)}
              </ProtectedRoute>
            }
          />

          <Route
            path="/usb-approval"
            element={
              <ProtectedRoute>
                {shell(<USBApproval />)}
              </ProtectedRoute>
            }
          />

          <Route
            path="/exam-mode"
            element={
              <ProtectedRoute>
                {shell(<ExamMode />)}
              </ProtectedRoute>
            }
          />

          <Route
            path="/cctv"
            element={
              <ProtectedRoute>
                {shell(<Cctv />)}
              </ProtectedRoute>
            }
          />

          <Route
            path="/os-deployment"
            element={
              <ProtectedRoute>
                {shell(<OsDeployment />)}
              </ProtectedRoute>
            }
          />

          <Route
            path="/endpoint-activity"
            element={
              <ProtectedRoute>
                {shell(<EndpointActivity />)}
              </ProtectedRoute>
            }
          />

          <Route
            path="/software-deployment"
            element={
              <ProtectedRoute>
                {shell(<SoftwareDeployment />)}
              </ProtectedRoute>
            }
          />

          <Route
            path="/threats"
            element={
              <ProtectedRoute>
                {shell(<Threats />)}
              </ProtectedRoute>
            }
          />

          <Route
            path="/web-access"
            element={
              <ProtectedRoute>
                {shell(<WebAccessControl />)}
              </ProtectedRoute>
            }
          />

          <Route
            path="/lab2"
            element={
              <ProtectedRoute>
                {shell(<Lab2 />)}
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