import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import BookingPage from "@/pages/BookingPage";
import ConfirmationPage from "@/pages/ConfirmationPage";
import AdminLoginPage from "@/pages/AdminLoginPage";
import AdminDashboard from "@/pages/AdminDashboard";
// Subcontracting pages
import ClaimPage from "@/pages/ClaimPage";
import DriverLoginPage from "@/pages/driver/DriverLoginPage";
import DriverCoursesPage from "@/pages/driver/DriverCoursesPage";
import DriverProfilePage from "@/pages/driver/DriverProfilePage";
import DriverRidePage from "@/pages/driver/DriverRidePage";
import AdminSubcontractingPage from "@/pages/admin/AdminSubcontractingPage";
import AdminCommissionsPage from "@/pages/admin/AdminCommissionsPage";
import AdminDangerZone from "@/pages/admin/AdminDangerZone";
import PaymentSuccessPage from "@/pages/PaymentSuccessPage";
// Client portal
import ClientPortalPage from "@/pages/ClientPortalPage";
import ConfirmRidePage from "@/pages/ConfirmRidePage";

function App() {
  return (
    <div className="app-container">
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/" element={<BookingPage />} />
          <Route path="/confirmation/:id" element={<ConfirmationPage />} />
          
          {/* Client portal (token-based, no auth) */}
          <Route path="/my-booking/:token" element={<ClientPortalPage />} />
          <Route path="/client/:token" element={<ClientPortalPage />} />
          <Route path="/confirm-ride/:rideId" element={<ConfirmRidePage />} />
          
          {/* Admin routes */}
          <Route path="/admin" element={<AdminLoginPage />} />
          <Route path="/admin/dashboard" element={<AdminDashboard />} />
          <Route path="/admin/subcontracting" element={<AdminSubcontractingPage />} />
          <Route path="/admin/commissions" element={<AdminCommissionsPage />} />
          
          {/* Driver routes */}
          <Route path="/driver/login" element={<DriverLoginPage />} />
          <Route path="/driver/courses" element={<DriverCoursesPage />} />
          <Route path="/driver/profile" element={<DriverProfilePage />} />
          <Route path="/driver/ride/:rideId" element={<DriverRidePage />} />
          
          {/* Claim route (subcontracting) */}
          <Route path="/claim/:token" element={<ClaimPage />} />
          
          {/* Payment success page */}
          <Route path="/payment/success" element={<PaymentSuccessPage />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-center" richColors />
    </div>
  );
}

export default App;
