import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function DriverLoginPage() {
  const navigate = useNavigate();
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  
  // Set driver manifest and apple-touch-icon for PWA
  useEffect(() => {
    // Update manifest to driver version with cache bust
    const manifestLink = document.querySelector('link[rel="manifest"]');
    if (manifestLink) manifestLink.href = '/manifest-driver.json?v=5';
    
    // Update apple-touch-icon to driver version
    const appleIcon = document.querySelector('link[rel="apple-touch-icon"]');
    if (appleIcon) appleIcon.href = '/icons/driver/apple-touch-icon.png?v=5';
    
    // No cleanup - keep driver manifest even on unmount for PWA consistency
  }, []);
  
  const [loginData, setLoginData] = useState({ email: '', password: '' });
  const [registerData, setRegisterData] = useState({
    email: '',
    password: '',
    company_name: '',
    name: '',
    phone: '',
    address: '',
    siret: '',
    vat_mention: 'TVA non applicable – art. 293 B du CGI',
    vat_applicable: false,
    vat_number: ''
  });

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const res = await fetch(`${API_URL}/api/driver/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(loginData)
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || 'Erreur de connexion');
      }
      
      localStorage.setItem('driver_token', data.token);
      localStorage.setItem('driver_info', JSON.stringify(data.driver));
      toast.success('Connexion réussie');
      navigate('/driver/courses');
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const res = await fetch(`${API_URL}/api/driver/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(registerData)
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || 'Erreur inscription');
      }
      
      toast.success('Inscription réussie ! Votre compte doit être validé par l\'administrateur.');
      setIsLogin(true);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <Card className="w-full max-w-md bg-slate-800/50 border-slate-700">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl text-white">
            {isLogin ? 'Connexion Chauffeur' : 'Inscription Chauffeur'}
          </CardTitle>
          <CardDescription className="text-slate-400">
            {isLogin 
              ? 'Accédez à votre espace chauffeur' 
              : 'Créez votre compte pour recevoir des courses'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLogin ? (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <Label className="text-slate-300">Email</Label>
                <Input
                  type="email"
                  value={loginData.email}
                  onChange={(e) => setLoginData({...loginData, email: e.target.value})}
                  className="bg-slate-700 border-slate-600 text-white"
                  required
                  data-testid="driver-login-email"
                />
              </div>
              <div>
                <Label className="text-slate-300">Mot de passe</Label>
                <Input
                  type="password"
                  value={loginData.password}
                  onChange={(e) => setLoginData({...loginData, password: e.target.value})}
                  className="bg-slate-700 border-slate-600 text-white"
                  required
                  data-testid="driver-login-password"
                />
              </div>
              <Button 
                type="submit" 
                className="w-full bg-sky-500 hover:bg-sky-600"
                disabled={loading}
                data-testid="driver-login-submit"
              >
                {loading ? 'Connexion...' : 'Se connecter'}
              </Button>
            </form>
          ) : (
            <form onSubmit={handleRegister} className="space-y-4 max-h-[60vh] overflow-y-auto pr-2">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-slate-300 text-sm">Nom complet *</Label>
                  <Input
                    value={registerData.name}
                    onChange={(e) => setRegisterData({...registerData, name: e.target.value})}
                    className="bg-slate-700 border-slate-600 text-white text-sm"
                    required
                  />
                </div>
                <div>
                  <Label className="text-slate-300 text-sm">Nom commercial *</Label>
                  <Input
                    value={registerData.company_name}
                    onChange={(e) => setRegisterData({...registerData, company_name: e.target.value})}
                    className="bg-slate-700 border-slate-600 text-white text-sm"
                    required
                  />
                </div>
              </div>
              <div>
                <Label className="text-slate-300 text-sm">Email *</Label>
                <Input
                  type="email"
                  value={registerData.email}
                  onChange={(e) => setRegisterData({...registerData, email: e.target.value})}
                  className="bg-slate-700 border-slate-600 text-white text-sm"
                  required
                />
              </div>
              <div>
                <Label className="text-slate-300 text-sm">Mot de passe *</Label>
                <Input
                  type="password"
                  value={registerData.password}
                  onChange={(e) => setRegisterData({...registerData, password: e.target.value})}
                  className="bg-slate-700 border-slate-600 text-white text-sm"
                  required
                />
              </div>
              <div>
                <Label className="text-slate-300 text-sm">Téléphone *</Label>
                <Input
                  value={registerData.phone}
                  onChange={(e) => setRegisterData({...registerData, phone: e.target.value})}
                  className="bg-slate-700 border-slate-600 text-white text-sm"
                  required
                />
              </div>
              <div>
                <Label className="text-slate-300 text-sm">Adresse professionnelle *</Label>
                <Input
                  value={registerData.address}
                  onChange={(e) => setRegisterData({...registerData, address: e.target.value})}
                  className="bg-slate-700 border-slate-600 text-white text-sm"
                  required
                />
              </div>
              <div>
                <Label className="text-slate-300 text-sm">SIRET *</Label>
                <Input
                  value={registerData.siret}
                  onChange={(e) => setRegisterData({...registerData, siret: e.target.value})}
                  className="bg-slate-700 border-slate-600 text-white text-sm"
                  placeholder="12345678900012"
                  required
                />
              </div>
              <div>
                <Label className="text-slate-300 text-sm">Mention TVA *</Label>
                <Input
                  value={registerData.vat_mention}
                  onChange={(e) => setRegisterData({...registerData, vat_mention: e.target.value})}
                  className="bg-slate-700 border-slate-600 text-white text-sm"
                  placeholder="TVA non applicable – art. 293 B du CGI"
                  required
                />
                <p className="text-slate-400 text-xs mt-1">Ex: "TVA non applicable – art. 293 B du CGI" pour micro-entreprise</p>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="vat"
                  checked={registerData.vat_applicable}
                  onChange={(e) => setRegisterData({...registerData, vat_applicable: e.target.checked})}
                  className="rounded"
                />
                <Label htmlFor="vat" className="text-slate-300 text-sm">Assujetti à la TVA</Label>
              </div>
              {registerData.vat_applicable && (
                <div>
                  <Label className="text-slate-300 text-sm">N° TVA</Label>
                  <Input
                    value={registerData.vat_number}
                    onChange={(e) => setRegisterData({...registerData, vat_number: e.target.value})}
                    className="bg-slate-700 border-slate-600 text-white text-sm"
                    placeholder="FR12345678901"
                  />
                </div>
              )}
              <Button 
                type="submit" 
                className="w-full bg-sky-500 hover:bg-sky-600"
                disabled={loading}
                data-testid="driver-register-submit"
              >
                {loading ? 'Inscription...' : 'S\'inscrire'}
              </Button>
            </form>
          )}
          
          <div className="mt-4 text-center">
            <button
              onClick={() => setIsLogin(!isLogin)}
              className="text-sky-400 hover:text-sky-300 text-sm"
            >
              {isLogin ? 'Pas encore de compte ? S\'inscrire' : 'Déjà un compte ? Se connecter'}
            </button>
          </div>
          
          <div className="mt-4 pt-4 border-t border-slate-700 text-center">
            <Link to="/" className="text-slate-400 hover:text-white text-sm">
              ← Retour à l'accueil
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
