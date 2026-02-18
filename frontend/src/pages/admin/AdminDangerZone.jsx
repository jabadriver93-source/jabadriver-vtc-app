import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Trash2, RefreshCw, ArrowLeft, ShieldAlert, CheckCircle, XCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export default function AdminDangerZone() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [resetting, setResetting] = useState(false);
  const [preview, setPreview] = useState(null);
  const [confirmText, setConfirmText] = useState('');
  const [resetComplete, setResetComplete] = useState(null);

  const fetchPreview = useCallback(async () => {
    setLoading(true);
    try {
      const password = localStorage.getItem('adminPassword') || 'admin123';
      const res = await fetch(`${API}/api/admin/danger/reset-preview?password=${encodeURIComponent(password)}`);
      if (!res.ok) {
        if (res.status === 401) {
          toast.error('Session expirée');
          navigate('/admin/login');
          return;
        }
        throw new Error('Erreur chargement');
      }
      const data = await res.json();
      setPreview(data);
    } catch (err) {
      toast.error('Erreur: ' + err.message);
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    fetchPreview();
  }, [fetchPreview]);

  const handleReset = async () => {
    if (confirmText !== 'RESET-ALL-TEST') {
      toast.error('Texte de confirmation incorrect');
      return;
    }

    setResetting(true);
    try {
      const password = localStorage.getItem('adminPassword') || 'admin123';
      const res = await fetch(`${API}/api/admin/danger/reset-all`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirm: confirmText, password })
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Erreur reset');
      }

      setResetComplete(data);
      setConfirmText('');
      toast.success('Reset complet effectué !');
      
      // Refresh preview after reset
      await fetchPreview();
    } catch (err) {
      toast.error('Erreur: ' + err.message);
    } finally {
      setResetting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <RefreshCw className="w-8 h-8 text-sky-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 p-4 md:p-6">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/admin')}
            className="text-slate-400 hover:text-white"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Retour Dashboard
          </Button>
        </div>

        {/* Title Card */}
        <Card className="bg-red-950/30 border-red-500/50">
          <CardHeader>
            <div className="flex items-center gap-3">
              <ShieldAlert className="w-8 h-8 text-red-500" />
              <div>
                <CardTitle className="text-red-400 text-xl">🧨 DANGER ZONE</CardTitle>
                <CardDescription className="text-red-300/70">
                  Reset total des données de test - Action irréversible
                </CardDescription>
              </div>
            </div>
          </CardHeader>
        </Card>

        {/* Status Card */}
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white text-lg flex items-center gap-2">
              {preview?.enabled ? (
                <CheckCircle className="w-5 h-5 text-green-500" />
              ) : (
                <XCircle className="w-5 h-5 text-red-500" />
              )}
              Statut: {preview?.enabled ? 'Activé' : 'Désactivé'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!preview?.enabled && (
              <p className="text-yellow-400 text-sm">
                ⚠️ Le reset est désactivé. Définissez ALLOW_DANGER_RESET=true dans les variables d'environnement pour l'activer.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Preview Card */}
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white text-lg">📊 Données à supprimer</CardTitle>
            <CardDescription className="text-slate-400">
              Aperçu des collections qui seront vidées
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {preview?.to_delete && (
              <div className="space-y-2">
                {Object.entries(preview.to_delete).map(([collection, count]) => (
                  <div 
                    key={collection} 
                    className="flex justify-between items-center p-3 bg-slate-700/50 rounded-lg"
                  >
                    <div>
                      <span className="text-white font-medium">{collection}</span>
                      <p className="text-slate-400 text-xs">
                        {preview.collections_info?.[collection] || ''}
                      </p>
                    </div>
                    <span className={`font-bold ${count > 0 ? 'text-red-400' : 'text-slate-500'}`}>
                      {count}
                    </span>
                  </div>
                ))}
                
                <div className="flex justify-between items-center p-3 bg-red-900/30 rounded-lg border border-red-500/30 mt-4">
                  <span className="text-red-300 font-bold">TOTAL À SUPPRIMER</span>
                  <span className="text-red-400 font-bold text-xl">
                    {preview.total_documents_to_delete}
                  </span>
                </div>
              </div>
            )}

            {preview?.preserved && (
              <div className="mt-6 pt-4 border-t border-slate-700">
                <h4 className="text-green-400 font-medium mb-2">✅ Données préservées</h4>
                {Object.entries(preview.preserved).map(([collection, count]) => (
                  <div 
                    key={collection} 
                    className="flex justify-between items-center p-2 bg-green-900/20 rounded"
                  >
                    <span className="text-green-300">{collection}</span>
                    <span className="text-green-400 font-medium">{count}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Reset Complete Card */}
        {resetComplete && (
          <Card className="bg-green-900/30 border-green-500/50">
            <CardHeader>
              <CardTitle className="text-green-400 text-lg flex items-center gap-2">
                <CheckCircle className="w-5 h-5" />
                Reset effectué avec succès
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <p className="text-green-300">
                Total supprimé: <span className="font-bold">{resetComplete.total_deleted}</span> documents
              </p>
              <div className="text-xs text-green-400/70 space-y-1">
                {Object.entries(resetComplete.deleted).map(([col, count]) => (
                  <div key={col}>{col}: {count} supprimés</div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Action Card */}
        {preview?.enabled && preview?.total_documents_to_delete > 0 && (
          <Card className="bg-red-950/50 border-red-500/50">
            <CardHeader>
              <CardTitle className="text-red-400 text-lg flex items-center gap-2">
                <AlertTriangle className="w-5 h-5" />
                Exécuter le reset
              </CardTitle>
              <CardDescription className="text-red-300/70">
                Cette action est IRRÉVERSIBLE. Toutes les données seront supprimées définitivement.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm text-red-300 mb-2 block">
                  Tapez <code className="bg-red-900/50 px-2 py-0.5 rounded">RESET-ALL-TEST</code> pour confirmer:
                </label>
                <Input
                  value={confirmText}
                  onChange={(e) => setConfirmText(e.target.value)}
                  placeholder="Tapez RESET-ALL-TEST"
                  className="bg-slate-800 border-red-500/50 text-white placeholder-slate-500"
                  data-testid="danger-confirm-input"
                />
              </div>
              
              <Button
                onClick={handleReset}
                disabled={confirmText !== 'RESET-ALL-TEST' || resetting}
                className="w-full bg-red-600 hover:bg-red-700 text-white disabled:opacity-50"
                data-testid="danger-reset-button"
              >
                {resetting ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Reset en cours...
                  </>
                ) : (
                  <>
                    <Trash2 className="w-4 h-4 mr-2" />
                    🧨 RESET TOTAL ({preview.total_documents_to_delete} documents)
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Empty State */}
        {preview?.total_documents_to_delete === 0 && (
          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="py-12 text-center">
              <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
              <p className="text-green-400 font-medium">Base de données déjà vide</p>
              <p className="text-slate-400 text-sm mt-2">
                Aucune donnée de test à supprimer.
              </p>
            </CardContent>
          </Card>
        )}

        {/* Refresh Button */}
        <Button
          variant="outline"
          onClick={fetchPreview}
          className="w-full border-slate-600 text-slate-300 hover:bg-slate-700"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Actualiser les compteurs
        </Button>
      </div>
    </div>
  );
}
