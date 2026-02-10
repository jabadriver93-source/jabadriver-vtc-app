import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Car, Lock, Loader2, ArrowLeft } from "lucide-react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

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
        // Store auth in sessionStorage
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
    <div className="min-h-screen bg-slate-900 flex flex-col">
      {/* Header */}
      <header className="px-6 py-6">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Car className="w-8 h-8 text-white" />
            <span className="text-2xl font-extrabold text-white tracking-tight" style={{ fontFamily: 'Manrope, sans-serif' }}>
              JABADRIVER
            </span>
          </div>
          <Button 
            variant="ghost" 
            onClick={() => navigate("/")}
            className="text-white/60 hover:text-white hover:bg-white/10"
            data-testid="back-to-booking"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Retour
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          {/* Title */}
          <div className="text-center mb-8 animate-fadeIn">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-white/10 rounded-2xl mb-4">
              <Lock className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-2xl font-extrabold text-white mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Espace Admin
            </h1>
            <p className="text-white/60">
              Accès réservé au chauffeur
            </p>
          </div>

          {/* Login Form */}
          <form 
            onSubmit={handleSubmit} 
            className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6 sm:p-8 animate-slideUp"
            data-testid="admin-login-form"
          >
            <div className="mb-6">
              <Label htmlFor="password" className="text-sm font-medium text-white/70 uppercase tracking-wider mb-2 block">
                Mot de passe
              </Label>
              <div className="relative">
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••"
                  className="pl-12 h-14 bg-white/10 border-white/20 text-white placeholder:text-white/40 focus:border-blue-500 rounded-xl"
                  data-testid="input-password"
                />
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/50" />
              </div>
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full h-14 bg-white hover:bg-white/90 text-slate-900 rounded-full font-semibold text-base btn-active"
              data-testid="submit-login"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 spinner" />
                  Connexion...
                </>
              ) : (
                "Se connecter"
              )}
            </Button>
          </form>
        </div>
      </main>
    </div>
  );
}
