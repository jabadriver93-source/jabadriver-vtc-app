import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, Save, AlertTriangle } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function DriverProfilePage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [profile, setProfile] = useState({
    company_name: '',
    name: '',
    phone: '',
    address: '',
    siret: '',
    vat_applicable: false,
    vat_number: '',
    invoice_prefix: 'DRI'
  });

  // Set driver manifest for PWA
  useEffect(() => {
    const manifestLink = document.querySelector('link[rel="manifest"]');
    if (manifestLink) manifestLink.href = '/manifest-driver.json?v=5';
    const appleIcon = document.querySelector('link[rel="apple-touch-icon"]');
    if (appleIcon) appleIcon.href = '/icons/driver/apple-touch-icon.png?v=5';
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('driver_token');
    if (!token) {
      navigate('/driver/login');
      return;
    }
    fetchProfile(token);
  }, [navigate]);

  const fetchProfile = async (token) => {
    try {
      const res = await fetch(`${API_URL}/api/driver/profile`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.status === 401 || res.status === 403) {
        localStorage.removeItem('driver_token');
        navigate('/driver/login');
        return;
      }
      
      const data = await res.json();
      setProfile(data);
    } catch (err) {
      toast.error('Erreur chargement profil');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    const token = localStorage.getItem('driver_token');
    
    try {
      const res = await fetch(`${API_URL}/api/driver/profile`, {
        method: 'PUT',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          company_name: profile.company_name,
          name: profile.name,
          phone: profile.phone,
          address: profile.address,
          siret: profile.siret,
          vat_applicable: profile.vat_applicable,
          vat_number: profile.vat_number,
          invoice_prefix: profile.invoice_prefix
        })
      });
      
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Erreur sauvegarde');
      }
      
      toast.success('Profil mis à jour');
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="text-white">Chargement...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-4 md:p-8">
      <div className="max-w-2xl mx-auto">
        <Button
          variant="ghost"
          onClick={() => navigate('/driver/courses')}
          className="mb-4 text-slate-400 hover:text-white"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Retour aux courses
        </Button>
        
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader>
            <CardTitle className="text-xl text-white">Mon Profil</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSave} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label className="text-slate-300">Nom complet</Label>
                  <Input
                    value={profile.name || ''}
                    onChange={(e) => setProfile({...profile, name: e.target.value})}
                    className="bg-slate-700 border-slate-600 text-white"
                    data-testid="profile-name"
                  />
                </div>
                <div>
                  <Label className="text-slate-300">Nom commercial</Label>
                  <Input
                    value={profile.company_name || ''}
                    onChange={(e) => setProfile({...profile, company_name: e.target.value})}
                    className="bg-slate-700 border-slate-600 text-white"
                    data-testid="profile-company"
                  />
                </div>
              </div>
              
              <div>
                <Label className="text-slate-300">Email</Label>
                <Input
                  value={profile.email || ''}
                  disabled
                  className="bg-slate-700/50 border-slate-600 text-slate-400"
                />
              </div>
              
              <div>
                <Label className="text-slate-300">Téléphone</Label>
                <Input
                  value={profile.phone || ''}
                  onChange={(e) => setProfile({...profile, phone: e.target.value})}
                  className="bg-slate-700 border-slate-600 text-white"
                  data-testid="profile-phone"
                />
              </div>
              
              <div>
                <Label className="text-slate-300">Adresse professionnelle</Label>
                <Input
                  value={profile.address || ''}
                  onChange={(e) => setProfile({...profile, address: e.target.value})}
                  className="bg-slate-700 border-slate-600 text-white"
                  data-testid="profile-address"
                />
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label className="text-slate-300">SIRET</Label>
                  <Input
                    value={profile.siret || ''}
                    onChange={(e) => setProfile({...profile, siret: e.target.value})}
                    className="bg-slate-700 border-slate-600 text-white"
                    data-testid="profile-siret"
                  />
                </div>
                <div>
                  <Label className="text-slate-300">Préfixe factures</Label>
                  <Input
                    value={profile.invoice_prefix || ''}
                    onChange={(e) => setProfile({...profile, invoice_prefix: e.target.value})}
                    className="bg-slate-700 border-slate-600 text-white"
                    data-testid="profile-prefix"
                  />
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="vat"
                  checked={profile.vat_applicable || false}
                  onChange={(e) => setProfile({...profile, vat_applicable: e.target.checked})}
                  className="rounded"
                />
                <Label htmlFor="vat" className="text-slate-300">Assujetti à la TVA</Label>
              </div>
              
              {profile.vat_applicable && (
                <div>
                  <Label className="text-slate-300">N° TVA intracommunautaire</Label>
                  <Input
                    value={profile.vat_number || ''}
                    onChange={(e) => setProfile({...profile, vat_number: e.target.value})}
                    className="bg-slate-700 border-slate-600 text-white"
                    data-testid="profile-vat"
                  />
                </div>
              )}
              
              <div className="pt-4 border-t border-slate-700">
                <p className="text-slate-400 text-sm mb-2">
                  Prochain numéro de facture: <span className="text-white">{profile.invoice_prefix}-{new Date().getFullYear()}-{String(profile.invoice_next_number || 1).padStart(4, '0')}</span>
                </p>
              </div>
              
              {/* Late Cancellations Section */}
              <div className="pt-4 border-t border-slate-700">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className={`w-4 h-4 ${(profile.late_cancellation_count || 0) >= 3 ? 'text-red-400' : (profile.late_cancellation_count || 0) >= 1 ? 'text-orange-400' : 'text-green-400'}`} />
                  <span className="text-slate-300 text-sm font-medium">Annulations tardives :</span>
                  <span className={`font-bold ${(profile.late_cancellation_count || 0) >= 3 ? 'text-red-400' : (profile.late_cancellation_count || 0) >= 1 ? 'text-orange-400' : 'text-green-400'}`} data-testid="late-cancellation-counter">
                    {profile.late_cancellation_count || 0} / 3
                  </span>
                </div>
                <p className="text-slate-500 text-xs">
                  ⚠️ 3 annulations tardives (moins d'1h avant la prise en charge) entraînent une désactivation automatique du compte.
                </p>
              </div>
              
              <Button 
                type="submit" 
                className="w-full bg-sky-500 hover:bg-sky-600"
                disabled={saving}
                data-testid="profile-save"
              >
                <Save className="w-4 h-4 mr-2" />
                {saving ? 'Sauvegarde...' : 'Sauvegarder'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
