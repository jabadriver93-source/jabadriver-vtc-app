import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { 
  Plus, Copy, RefreshCw, XCircle, CheckCircle, Users, 
  FileText, MapPin, Clock, Euro, ArrowLeft, Trash2, UserCheck, UserX, RotateCcw, AlertTriangle, FlaskConical
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function AdminSubcontractingPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('courses');
  const [courses, setCourses] = useState([]);
  const [drivers, setDrivers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showTestRides, setShowTestRides] = useState(false); // Filter: default OFF = hide test rides
  const [newCourse, setNewCourse] = useState({
    client_name: '',
    client_email: '',
    client_phone: '',
    pickup_address: '',
    dropoff_address: '',
    date: '',
    time: '',
    distance_km: '',
    price_total: '',
    notes: ''
  });

  useEffect(() => {
    // Check admin auth (simple check)
    const isAdmin = sessionStorage.getItem('adminAuth');
    if (!isAdmin) {
      navigate('/admin');
      return;
    }
    fetchData();
  }, [navigate]);

  const fetchData = async () => {
    try {
      const [coursesRes, driversRes] = await Promise.all([
        fetch(`${API_URL}/api/admin/subcontracting/courses`),
        fetch(`${API_URL}/api/admin/subcontracting/drivers`)
      ]);
      
      setCourses(await coursesRes.json());
      setDrivers(await driversRes.json());
    } catch (err) {
      toast.error('Erreur chargement données');
    } finally {
      setLoading(false);
    }
  };

  const createCourse = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...newCourse,
        distance_km: newCourse.distance_km ? parseFloat(newCourse.distance_km) : null,
        price_total: parseFloat(newCourse.price_total)
      };
      
      const res = await fetch(`${API_URL}/api/admin/subcontracting/courses`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      
      toast.success('Course créée');
      
      // Copy claim URL
      const claimUrl = `${window.location.origin}/claim/${data.claim_token}`;
      navigator.clipboard.writeText(claimUrl);
      toast.success('Lien claim copié !');
      
      setShowCreateModal(false);
      setNewCourse({
        client_name: '', client_email: '', client_phone: '',
        pickup_address: '', dropoff_address: '',
        date: '', time: '', distance_km: '', price_total: '', notes: ''
      });
      fetchData();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const regenerateToken = async (courseId) => {
    try {
      const res = await fetch(`${API_URL}/api/admin/subcontracting/courses/${courseId}/regenerate-token`, {
        method: 'POST'
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      
      const claimUrl = `${window.location.origin}/claim/${data.claim_token}`;
      navigator.clipboard.writeText(claimUrl);
      toast.success('Nouveau lien copié !');
      fetchData();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const resetToOpen = async (courseId) => {
    try {
      const res = await fetch(`${API_URL}/api/admin/subcontracting/courses/${courseId}/reset-to-open`, {
        method: 'POST'
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      toast.success(data.message);
      fetchData();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const cancelCourse = async (courseId) => {
    if (!window.confirm('Annuler cette course ?')) return;
    try {
      const res = await fetch(`${API_URL}/api/admin/subcontracting/courses/${courseId}/cancel`, {
        method: 'POST'
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      toast.success(data.message);
      fetchData();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const markDone = async (courseId) => {
    try {
      const res = await fetch(`${API_URL}/api/admin/subcontracting/courses/${courseId}/mark-done`, {
        method: 'POST'
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      toast.success(data.message);
      fetchData();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const activateDriver = async (driverId) => {
    try {
      const res = await fetch(`${API_URL}/api/admin/subcontracting/drivers/${driverId}/activate`, {
        method: 'POST'
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      toast.success('Chauffeur activé');
      fetchData();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const deactivateDriver = async (driverId) => {
    try {
      const res = await fetch(`${API_URL}/api/admin/subcontracting/drivers/${driverId}/deactivate`, {
        method: 'POST'
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      toast.success('Chauffeur désactivé');
      fetchData();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const deleteDriver = async (driverId) => {
    if (!window.confirm('Supprimer ce chauffeur ?')) return;
    try {
      const res = await fetch(`${API_URL}/api/admin/subcontracting/drivers/${driverId}`, {
        method: 'DELETE'
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      toast.success('Chauffeur supprimé');
      fetchData();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const copyClaimLink = (course) => {
    const token = course.claim_tokens?.[0]?.token;
    if (token) {
      const url = `${window.location.origin}/claim/${token}`;
      navigator.clipboard.writeText(url);
      toast.success('Lien copié !');
    } else {
      toast.error('Aucun token actif');
    }
  };

  const toggleTestCourse = async (courseId, currentIsTest) => {
    try {
      const res = await fetch(`${API_URL}/api/admin/subcontracting/courses/${courseId}/toggle-test`, {
        method: 'POST'
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      
      // Update local state
      setCourses(prev => prev.map(c => 
        c.id === courseId ? { ...c, is_test: data.is_test } : c
      ));
      
      toast.success(data.message);
    } catch (err) {
      toast.error(err.message);
    }
  };

  const downloadCommissionInvoice = async (courseId) => {
    try {
      const res = await fetch(`${API_URL}/api/admin/subcontracting/courses/${courseId}/commission-invoice-pdf`);
      if (!res.ok) throw new Error('Erreur téléchargement');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `commission_${courseId.slice(0,8)}.pdf`;
      a.click();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'OPEN': return 'bg-sky-500/20 text-sky-400 border-sky-500/30';
      case 'RESERVED': return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'ASSIGNED': return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'DONE': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'CANCELLED': return 'bg-red-500/20 text-red-400 border-red-500/30';
      default: return 'bg-slate-500/20 text-slate-400';
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
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/admin/dashboard')}
              className="text-slate-400 hover:text-white mb-2"
            >
              <ArrowLeft className="w-4 h-4 mr-1" />
              Retour Dashboard
            </Button>
            <h1 className="text-2xl font-bold text-white">Sous-traitance</h1>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => navigate('/admin/commissions')}
              className="border-green-600 text-green-400 hover:bg-green-900/30"
              data-testid="commissions-history-btn"
            >
              <Euro className="w-4 h-4 mr-2" />
              Commissions
            </Button>
            <Button
              className="bg-sky-600 hover:bg-sky-700"
              onClick={() => setShowCreateModal(true)}
              data-testid="create-course-btn"
            >
              <Plus className="w-4 h-4 mr-2" />
              Nouvelle course
            </Button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          <Button
            variant={activeTab === 'courses' ? 'default' : 'outline'}
            onClick={() => setActiveTab('courses')}
            className={activeTab === 'courses' ? 'bg-sky-600' : 'border-slate-600 text-slate-300'}
          >
            Courses ({courses.length})
          </Button>
          <Button
            variant={activeTab === 'drivers' ? 'default' : 'outline'}
            onClick={() => setActiveTab('drivers')}
            className={activeTab === 'drivers' ? 'bg-sky-600' : 'border-slate-600 text-slate-300'}
          >
            <Users className="w-4 h-4 mr-2" />
            Chauffeurs ({drivers.length})
          </Button>
        </div>

        {/* Courses Tab */}
        {activeTab === 'courses' && (
          <div className="space-y-4">
            {courses.length === 0 ? (
              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="py-12 text-center">
                  <p className="text-slate-400">Aucune course sous-traitée</p>
                </CardContent>
              </Card>
            ) : (
              courses.map((course) => (
                <Card key={course.id} className={`bg-slate-800/50 border-slate-700 ${course.is_test ? 'ring-2 ring-orange-500/50' : ''}`} data-testid={`admin-course-${course.id}`}>
                  <CardContent className="p-4">
                    <div className="flex justify-between items-start mb-3">
                      <div className="flex items-center gap-2">
                        <span className="text-white font-medium">{course.client_name}</span>
                        <span className="text-slate-500 text-sm">#{course.id.slice(0,8)}</span>
                        {course.is_test && (
                          <span className="px-2 py-0.5 rounded text-xs font-medium bg-orange-500/20 text-orange-400 border border-orange-500/30 flex items-center gap-1" data-testid={`test-badge-${course.id}`}>
                            <FlaskConical className="w-3 h-3" />
                            TEST
                          </span>
                        )}
                      </div>
                      <span className={`px-2 py-1 rounded text-xs border ${getStatusColor(course.status)}`}>
                        {course.status}
                      </span>
                    </div>
                    
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3 text-sm">
                      <div className="flex items-center gap-2 text-slate-400">
                        <Clock className="w-4 h-4" />
                        {course.date} {course.time}
                      </div>
                      <div className="flex items-center gap-2 text-sky-400">
                        <Euro className="w-4 h-4" />
                        {course.price_total?.toFixed(2)} €
                        {course.is_test && <span className="text-orange-400 text-xs">(test)</span>}
                      </div>
                      <div className="flex items-center gap-2 text-amber-400">
                        Commission: {course.commission_amount?.toFixed(2)} €
                      </div>
                      <div className="flex items-center gap-2">
                        {course.commission_paid ? (
                          <span className="text-green-400 flex items-center gap-1">
                            <CheckCircle className="w-4 h-4" /> Payée
                          </span>
                        ) : (
                          <span className="text-slate-500">Non payée</span>
                        )}
                      </div>
                    </div>
                    
                    <div className="text-sm text-slate-400 mb-3">
                      <span className="text-green-400">▶</span> {course.pickup_address?.slice(0,40)}...
                      <br />
                      <span className="text-red-400">◼</span> {course.dropoff_address?.slice(0,40)}...
                    </div>
                    
                    {course.assigned_driver && (
                      <div className="bg-slate-700/30 p-2 rounded mb-3 text-sm">
                        <span className="text-slate-400">Chauffeur:</span>
                        <span className="text-white ml-2">{course.assigned_driver.company_name}</span>
                        <span className="text-slate-500 ml-2">({course.assigned_driver.email})</span>
                      </div>
                    )}
                    
                    {/* Actions */}
                    <div className="flex flex-wrap gap-2 pt-3 border-t border-slate-700">
                      {/* Test Toggle Button - Always visible */}
                      <Button
                        size="sm"
                        variant="outline"
                        className={course.is_test 
                          ? "border-orange-600 text-orange-400 hover:bg-orange-900/30" 
                          : "border-slate-600 text-slate-300 hover:bg-slate-700/50"
                        }
                        onClick={() => toggleTestCourse(course.id, course.is_test)}
                        data-testid={`toggle-test-btn-${course.id}`}
                        title={course.is_test ? "Retirer du mode test" : "Marquer comme test"}
                      >
                        <FlaskConical className="w-4 h-4 mr-1" />
                        {course.is_test ? 'Mode Test' : 'Test'}
                      </Button>
                      
                      {course.status !== 'CANCELLED' && course.status !== 'DONE' && (
                        <>
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-slate-600 text-slate-300"
                            onClick={() => copyClaimLink(course)}
                          >
                            <Copy className="w-4 h-4 mr-1" />
                            Copier lien
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-slate-600 text-slate-300"
                            onClick={() => regenerateToken(course.id)}
                          >
                            <RefreshCw className="w-4 h-4 mr-1" />
                            Nouveau lien
                          </Button>
                        </>
                      )}
                      
                      {course.status === 'RESERVED' && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="border-amber-600 text-amber-400"
                          onClick={() => resetToOpen(course.id)}
                        >
                          <RotateCcw className="w-4 h-4 mr-1" />
                          Libérer
                        </Button>
                      )}
                      
                      {course.status === 'ASSIGNED' && (
                        <>
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-green-600 text-green-400"
                            onClick={() => markDone(course.id)}
                          >
                            <CheckCircle className="w-4 h-4 mr-1" />
                            Terminée
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-slate-600 text-slate-300"
                            onClick={() => downloadCommissionInvoice(course.id)}
                          >
                            <FileText className="w-4 h-4 mr-1" />
                            Facture commission
                          </Button>
                        </>
                      )}
                      
                      {course.status !== 'CANCELLED' && course.status !== 'DONE' && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="border-red-600 text-red-400"
                          onClick={() => cancelCourse(course.id)}
                        >
                          <XCircle className="w-4 h-4 mr-1" />
                          Annuler
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        )}

        {/* Drivers Tab */}
        {activeTab === 'drivers' && (
          <div className="space-y-4">
            {drivers.length === 0 ? (
              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="py-12 text-center">
                  <p className="text-slate-400">Aucun chauffeur inscrit</p>
                </CardContent>
              </Card>
            ) : (
              drivers.map((driver) => (
                <Card key={driver.id} className="bg-slate-800/50 border-slate-700" data-testid={`admin-driver-${driver.id}`}>
                  <CardContent className="p-4">
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <span className="text-white font-medium">{driver.company_name}</span>
                        <span className="text-slate-500 text-sm ml-2">({driver.name})</span>
                      </div>
                      <div className="flex items-center gap-2">
                        {/* Late cancellation badge */}
                        {(() => {
                          const count = driver.late_cancellation_count || 0;
                          let badgeColor = 'bg-green-500/20 text-green-400 border-green-500/30';
                          if (count >= 3) badgeColor = 'bg-red-500/20 text-red-400 border-red-500/30';
                          else if (count >= 1) badgeColor = 'bg-orange-500/20 text-orange-400 border-orange-500/30';
                          return (
                            <span 
                              className={`px-2 py-1 rounded text-xs border flex items-center gap-1 ${badgeColor}`}
                              title="Annulations tardives"
                              data-testid={`driver-late-count-${driver.id}`}
                            >
                              <AlertTriangle className="w-3 h-3" />
                              {count}/3
                            </span>
                          );
                        })()}
                        <span className={`px-2 py-1 rounded text-xs border ${driver.is_active ? 'bg-green-500/20 text-green-400 border-green-500/30' : 'bg-red-500/20 text-red-400 border-red-500/30'}`}>
                          {driver.is_active ? 'Actif' : 'En attente'}
                        </span>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-2 text-sm text-slate-400 mb-3">
                      <div>Email: {driver.email}</div>
                      <div>Tél: {driver.phone}</div>
                      <div>SIRET: {driver.siret}</div>
                      <div>TVA: {driver.vat_applicable ? driver.vat_number || 'Oui' : 'Non'}</div>
                    </div>
                    
                    <div className="flex gap-2 pt-3 border-t border-slate-700">
                      {!driver.is_active ? (
                        <Button
                          size="sm"
                          className="bg-green-600 hover:bg-green-700"
                          onClick={() => activateDriver(driver.id)}
                        >
                          <UserCheck className="w-4 h-4 mr-1" />
                          Activer
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          className="border-amber-600 text-amber-400"
                          onClick={() => deactivateDriver(driver.id)}
                        >
                          <UserX className="w-4 h-4 mr-1" />
                          Désactiver
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="outline"
                        className="border-red-600 text-red-400"
                        onClick={() => deleteDriver(driver.id)}
                      >
                        <Trash2 className="w-4 h-4 mr-1" />
                        Supprimer
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        )}

        {/* Create Course Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
            <Card className="w-full max-w-lg bg-slate-800 border-slate-700 max-h-[90vh] overflow-y-auto">
              <CardHeader>
                <CardTitle className="text-white">Nouvelle course sous-traitée</CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={createCourse} className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label className="text-slate-300 text-sm">Nom client *</Label>
                      <Input
                        value={newCourse.client_name}
                        onChange={(e) => setNewCourse({...newCourse, client_name: e.target.value})}
                        className="bg-slate-700 border-slate-600 text-white"
                        required
                      />
                    </div>
                    <div>
                      <Label className="text-slate-300 text-sm">Téléphone client *</Label>
                      <Input
                        value={newCourse.client_phone}
                        onChange={(e) => setNewCourse({...newCourse, client_phone: e.target.value})}
                        className="bg-slate-700 border-slate-600 text-white"
                        required
                      />
                    </div>
                  </div>
                  
                  <div>
                    <Label className="text-slate-300 text-sm">Email client *</Label>
                    <Input
                      type="email"
                      value={newCourse.client_email}
                      onChange={(e) => setNewCourse({...newCourse, client_email: e.target.value})}
                      className="bg-slate-700 border-slate-600 text-white"
                      required
                    />
                  </div>
                  
                  <div>
                    <Label className="text-slate-300 text-sm">Adresse départ *</Label>
                    <Input
                      value={newCourse.pickup_address}
                      onChange={(e) => setNewCourse({...newCourse, pickup_address: e.target.value})}
                      className="bg-slate-700 border-slate-600 text-white"
                      required
                    />
                  </div>
                  
                  <div>
                    <Label className="text-slate-300 text-sm">Adresse arrivée *</Label>
                    <Input
                      value={newCourse.dropoff_address}
                      onChange={(e) => setNewCourse({...newCourse, dropoff_address: e.target.value})}
                      className="bg-slate-700 border-slate-600 text-white"
                      required
                    />
                  </div>
                  
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <Label className="text-slate-300 text-sm">Date *</Label>
                      <Input
                        type="date"
                        value={newCourse.date}
                        onChange={(e) => setNewCourse({...newCourse, date: e.target.value})}
                        className="bg-slate-700 border-slate-600 text-white"
                        required
                      />
                    </div>
                    <div>
                      <Label className="text-slate-300 text-sm">Heure *</Label>
                      <Input
                        type="time"
                        value={newCourse.time}
                        onChange={(e) => setNewCourse({...newCourse, time: e.target.value})}
                        className="bg-slate-700 border-slate-600 text-white"
                        required
                      />
                    </div>
                    <div>
                      <Label className="text-slate-300 text-sm">Distance (km)</Label>
                      <Input
                        type="number"
                        step="0.1"
                        value={newCourse.distance_km}
                        onChange={(e) => setNewCourse({...newCourse, distance_km: e.target.value})}
                        className="bg-slate-700 border-slate-600 text-white"
                      />
                    </div>
                  </div>
                  
                  <div>
                    <Label className="text-slate-300 text-sm">Prix total (€) *</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={newCourse.price_total}
                      onChange={(e) => setNewCourse({...newCourse, price_total: e.target.value})}
                      className="bg-slate-700 border-slate-600 text-white"
                      required
                    />
                    {newCourse.price_total && (
                      <p className="text-amber-400 text-sm mt-1">
                        Commission: {(parseFloat(newCourse.price_total) * 0.10).toFixed(2)} €
                      </p>
                    )}
                  </div>
                  
                  <div>
                    <Label className="text-slate-300 text-sm">Notes</Label>
                    <Input
                      value={newCourse.notes}
                      onChange={(e) => setNewCourse({...newCourse, notes: e.target.value})}
                      className="bg-slate-700 border-slate-600 text-white"
                      placeholder="Instructions spéciales..."
                    />
                  </div>
                  
                  <div className="flex gap-2 pt-4">
                    <Button
                      type="button"
                      variant="outline"
                      className="flex-1 border-slate-600 text-slate-300"
                      onClick={() => setShowCreateModal(false)}
                    >
                      Annuler
                    </Button>
                    <Button type="submit" className="flex-1 bg-sky-600 hover:bg-sky-700">
                      Créer et copier le lien
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
