import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Lock, Loader2, ArrowLeft } from "lucide-react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const LOGO_URL = "/logo.png";

export default function AdminLoginPage() {
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!password) {
      toast.error("Veuillez entrer le mot de passe");
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API}/admin/login`, { password });
      if (response.data.success) {
        sessionStorage.setItem("adminAuth", "true");
        toast.success("Connexion réussie");
        navigate("/admin/dashboard");
      }
    } catch (error) {
      console.error("Login error:", error);
      toast.error("Mot de passe incorrect");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] flex flex-col">
      {/* Header */}
      <header className="px-5 py-5 border-b border-white/10">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src={LOGO_URL} alt="JABA DRIVER" className="h-10 w-auto" />
            <span className="text-xl font-bold text-white tracking-tight hidden sm:block" style={{ fontFamily: 'Manrope, sans-serif' }}>
              JABA DRIVER
            </span>
          </div>
          <button 
            onClick={() => navigate("/")}
            className="inline-flex items-center gap-2 text-white/40 hover:text-white/70 text-sm font-medium transition-colors"
            data-testid="back-to-booking"
          >
            <ArrowLeft className="w-4 h-4" />
            Retour
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center px-5 py-12">
        <div className="w-full max-w-sm">
          {/* Title */}
          <div className="text-center mb-10 animate-fadeIn">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-white/5 border border-white/10 rounded-2xl mb-5">
              <Lock className="w-9 h-9 text-[#7dd3fc]" />
            </div>
            <h1 
              className="text-3xl font-bold text-white mb-2" 
              style={{ fontFamily: 'Manrope, sans-serif' }}
            >
              Espace Admin
            </h1>
            <p className="text-white/40">
              Accès réservé au chauffeur
            </p>
          </div>

          {/* Login Form */}
          <form 
            onSubmit={handleSubmit} 
            className="card-dark p-6 sm:p-8 animate-slideUp"
            data-testid="admin-login-form"
          >
            <div className="mb-6">
              <label htmlFor="password" className="block text-sm font-medium text-white/50 mb-2 uppercase tracking-wider">
                Mot de passe
              </label>
              <div className="relative">
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••"
                  className="w-full h-14 bg-white/5 border border-white/15 rounded-xl px-4 pl-12 text-white placeholder:text-white/30 focus:outline-none focus:border-[#7dd3fc]"
                  data-testid="input-password"
                />
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/30" />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full h-14 bg-[#7dd3fc] hover:bg-[#93dcfc] text-[#0a0a0a] rounded-xl font-semibold text-base transition-colors flex items-center justify-center gap-2"
              data-testid="submit-login"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 spinner" />
                  Connexion...
                </>
              ) : (
                "Se connecter"
              )}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
