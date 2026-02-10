import { useState } from 'react';
import '@/App.css';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import ReservationPage from '@/pages/ReservationPage';
import AdminDashboard from '@/pages/AdminDashboard';
import { Toaster } from '@/components/ui/sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const HomePage = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-gray-900 mb-4" data-testid="home-title">
            🚕 JabaDriver VTC
          </h1>
          <p className="text-xl text-gray-700 mb-8">
            Votre service de transport avec chauffeur professionnel
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          <Link to="/reservation" data-testid="reservation-link">
            <div className="bg-white rounded-lg shadow-lg p-8 hover:shadow-xl transition-shadow cursor-pointer border-2 border-transparent hover:border-blue-500">
              <div className="text-4xl mb-4">📝</div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Nouvelle Réservation
              </h2>
              <p className="text-gray-600">
                Réservez votre course VTC en quelques clics
              </p>
            </div>
          </Link>

          <Link to="/admin" data-testid="admin-link">
            <div className="bg-white rounded-lg shadow-lg p-8 hover:shadow-xl transition-shadow cursor-pointer border-2 border-transparent hover:border-indigo-500">
              <div className="text-4xl mb-4">⚙️</div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Dashboard Admin
              </h2>
              <p className="text-gray-600">
                Gérer les réservations et générer les documents
              </p>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/reservation" element={<ReservationPage />} />
          <Route path="/admin" element={<AdminDashboard />} />
        </Routes>
      </BrowserRouter>
      <Toaster richColors position="top-right" />
    </div>
  );
}

export default App;
