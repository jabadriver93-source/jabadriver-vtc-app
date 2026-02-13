import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { 
  ArrowLeft, Download, RefreshCw, Filter, Euro, Calendar, 
  User, CreditCard, CheckCircle, XCircle, Clock, ExternalLink
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function AdminCommissionsPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [commissions, setCommissions] = useState([]);
  const [totalCommission, setTotalCommission] = useState(0);
  const [count, setCount] = useState(0);
  
  // Filters
  const [filters, setFilters] = useState({
    start_date: '',
    end_date: '',
    driver_id: '',
    status: '',
    test_mode: ''
  });
  const [showFilters, setShowFilters] = useState(false);
  const [drivers, setDrivers] = useState([]);

  useEffect(() => {
    const isAdmin = sessionStorage.getItem('adminAuth');
    if (!isAdmin) {
      navigate('/admin');
      return;
    }
    fetchDrivers();
    fetchCommissions();
  }, [navigate]);

  const fetchDrivers = async () => {
    try {
      const res = await fetch(`${API_URL}/api/admin/subcontracting/drivers`);
      setDrivers(await res.json());
    } catch (err) {
      console.error('Error fetching drivers:', err);
    }
  };

  const fetchCommissions = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      if (filters.driver_id) params.append('driver_id', filters.driver_id);
      if (filters.status) params.append('status', filters.status);
      if (filters.test_mode !== '') params.append('test_mode', filters.test_mode);
      
      const res = await fetch(`${API_URL}/api/admin/subcontracting/commissions?${params}`);
      const data = await res.json();
      
      setCommissions(data.payments || []);
      setTotalCommission(data.total_commission || 0);
      setCount(data.count || 0);
    } catch (err) {
      toast.error('Erreur chargement commissions');
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = async () => {
    try {
      const params = new URLSearchParams();
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      if (filters.driver_id) params.append('driver_id', filters.driver_id);
      if (filters.status) params.append('status', filters.status);
      
      const res = await fetch(`${API_URL}/api/admin/subcontracting/commissions/export-csv?${params}`);
      const blob = await res.blob();
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `commissions_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Export CSV téléchargé');
    } catch (err) {
      toast.error('Erreur export CSV');
    }
  };

  const applyFilters = () => {
    fetchCommissions();
    setShowFilters(false);
  };

  const clearFilters = () => {
    setFilters({
      start_date: '',
      end_date: '',
      driver_id: '',
      status: '',
      test_mode: ''
    });
    setTimeout(() => fetchCommissions(), 100);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    try {
      const dt = new Date(dateStr);
      return dt.toLocaleDateString('fr-FR', { 
        day: '2-digit', 
        month: '2-digit', 
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr.slice(0, 16);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'paid':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
            <CheckCircle className="w-3 h-3" /> Payé
          </span>
        );
      case 'pending':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
            <Clock className="w-3 h-3" /> En attente
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
            <XCircle className="w-3 h-3" /> Échoué
          </span>
        );
      default:
        return (
          <span className="px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
          <div className="flex items-center gap-4">
            <Button 
              variant="ghost" 
              onClick={() => navigate('/admin/subcontracting')}
              className="text-gray-400 hover:text-white"
            >
              <ArrowLeft className="w-4 h-4 mr-2" /> Retour
            </Button>
            <div>
              <h1 className="text-2xl font-bold">💳 Historique Commissions</h1>
              <p className="text-gray-400 text-sm">Paiements de commission Stripe</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <Button 
              variant="outline" 
              onClick={() => setShowFilters(!showFilters)}
              className="border-gray-700"
            >
              <Filter className="w-4 h-4 mr-2" /> Filtres
            </Button>
            <Button 
              variant="outline" 
              onClick={handleExportCSV}
              className="border-gray-700"
            >
              <Download className="w-4 h-4 mr-2" /> Export CSV
            </Button>
            <Button onClick={fetchCommissions} disabled={loading}>
              <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Actualiser
            </Button>
          </div>
        </div>

        {/* Filters Panel */}
        {showFilters && (
          <Card className="bg-gray-900 border-gray-800 mb-6">
            <CardHeader>
              <CardTitle className="text-lg">Filtres</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                <div>
                  <Label className="text-gray-400">Date début</Label>
                  <Input 
                    type="date"
                    value={filters.start_date}
                    onChange={(e) => setFilters({...filters, start_date: e.target.value})}
                    className="bg-gray-800 border-gray-700"
                  />
                </div>
                <div>
                  <Label className="text-gray-400">Date fin</Label>
                  <Input 
                    type="date"
                    value={filters.end_date}
                    onChange={(e) => setFilters({...filters, end_date: e.target.value})}
                    className="bg-gray-800 border-gray-700"
                  />
                </div>
                <div>
                  <Label className="text-gray-400">Chauffeur</Label>
                  <select
                    value={filters.driver_id}
                    onChange={(e) => setFilters({...filters, driver_id: e.target.value})}
                    className="w-full h-10 px-3 rounded-md bg-gray-800 border border-gray-700 text-white"
                  >
                    <option value="">Tous</option>
                    {drivers.map(d => (
                      <option key={d.id} value={d.id}>{d.name} ({d.company_name})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <Label className="text-gray-400">Statut</Label>
                  <select
                    value={filters.status}
                    onChange={(e) => setFilters({...filters, status: e.target.value})}
                    className="w-full h-10 px-3 rounded-md bg-gray-800 border border-gray-700 text-white"
                  >
                    <option value="">Tous</option>
                    <option value="paid">Payé</option>
                    <option value="pending">En attente</option>
                    <option value="failed">Échoué</option>
                  </select>
                </div>
                <div>
                  <Label className="text-gray-400">Mode</Label>
                  <select
                    value={filters.test_mode}
                    onChange={(e) => setFilters({...filters, test_mode: e.target.value})}
                    className="w-full h-10 px-3 rounded-md bg-gray-800 border border-gray-700 text-white"
                  >
                    <option value="">Tous</option>
                    <option value="true">Test</option>
                    <option value="false">Live</option>
                  </select>
                </div>
              </div>
              <div className="flex gap-2 mt-4">
                <Button onClick={applyFilters}>Appliquer</Button>
                <Button variant="outline" onClick={clearFilters} className="border-gray-700">
                  Réinitialiser
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <Card className="bg-gradient-to-br from-green-900/50 to-green-800/30 border-green-700">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-green-500/20 rounded-full">
                  <Euro className="w-6 h-6 text-green-400" />
                </div>
                <div>
                  <p className="text-green-300 text-sm">Total Commissions</p>
                  <p className="text-3xl font-bold text-white">{totalCommission.toFixed(2)}€</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-gradient-to-br from-blue-900/50 to-blue-800/30 border-blue-700">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blue-500/20 rounded-full">
                  <CreditCard className="w-6 h-6 text-blue-400" />
                </div>
                <div>
                  <p className="text-blue-300 text-sm">Paiements</p>
                  <p className="text-3xl font-bold text-white">{count}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-gradient-to-br from-purple-900/50 to-purple-800/30 border-purple-700">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-purple-500/20 rounded-full">
                  <User className="w-6 h-6 text-purple-400" />
                </div>
                <div>
                  <p className="text-purple-300 text-sm">Chauffeurs actifs</p>
                  <p className="text-3xl font-bold text-white">
                    {new Set(commissions.filter(c => c.status === 'paid').map(c => c.driver_id)).size}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Commissions Table */}
        <Card className="bg-gray-900 border-gray-800">
          <CardHeader>
            <CardTitle>Détail des paiements</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex justify-center py-12">
                <RefreshCw className="w-8 h-8 animate-spin text-gray-500" />
              </div>
            ) : commissions.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <CreditCard className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>Aucun paiement trouvé</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm" data-testid="commissions-table">
                  <thead>
                    <tr className="border-b border-gray-800 text-left">
                      <th className="pb-3 text-gray-400 font-medium">Date</th>
                      <th className="pb-3 text-gray-400 font-medium">Réservation</th>
                      <th className="pb-3 text-gray-400 font-medium">Chauffeur</th>
                      <th className="pb-3 text-gray-400 font-medium text-right">Commission</th>
                      <th className="pb-3 text-gray-400 font-medium text-right">Course</th>
                      <th className="pb-3 text-gray-400 font-medium">Statut</th>
                      <th className="pb-3 text-gray-400 font-medium">PaymentIntent</th>
                      <th className="pb-3 text-gray-400 font-medium">Mode</th>
                    </tr>
                  </thead>
                  <tbody>
                    {commissions.map((payment, idx) => (
                      <tr key={payment.id || idx} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                        <td className="py-3">
                          <div className="flex items-center gap-2">
                            <Calendar className="w-4 h-4 text-gray-500" />
                            <span>{formatDate(payment.created_at)}</span>
                          </div>
                        </td>
                        <td className="py-3">
                          {payment.course ? (
                            <div>
                              <span className="font-mono text-xs bg-gray-800 px-2 py-1 rounded">
                                {payment.course.id?.slice(0, 8).toUpperCase()}
                              </span>
                              <div className="text-xs text-gray-500 mt-1">
                                {payment.course.pickup_city} → {payment.course.dropoff_city}
                              </div>
                            </div>
                          ) : (
                            <span className="text-gray-500">-</span>
                          )}
                        </td>
                        <td className="py-3">
                          {payment.driver ? (
                            <div>
                              <div className="font-medium">{payment.driver.name}</div>
                              <div className="text-xs text-gray-500">{payment.driver.company_name}</div>
                              <div className="text-xs text-gray-500">{payment.driver.email}</div>
                            </div>
                          ) : (
                            <span className="text-gray-500">-</span>
                          )}
                        </td>
                        <td className="py-3 text-right">
                          <span className="font-bold text-green-400">
                            {payment.amount?.toFixed(2)}€
                          </span>
                        </td>
                        <td className="py-3 text-right">
                          <span className="text-gray-300">
                            {payment.course?.price_total ? `${payment.course.price_total}€` : '-'}
                          </span>
                        </td>
                        <td className="py-3">
                          {getStatusBadge(payment.status)}
                        </td>
                        <td className="py-3">
                          {payment.provider_payment_id ? (
                            <div className="flex items-center gap-1">
                              <code className="text-xs bg-gray-800 px-2 py-1 rounded max-w-[120px] truncate">
                                {payment.provider_payment_id}
                              </code>
                              <a
                                href={`https://dashboard.stripe.com/payments/${payment.provider_payment_id}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-400 hover:text-blue-300"
                              >
                                <ExternalLink className="w-3 h-3" />
                              </a>
                            </div>
                          ) : (
                            <span className="text-gray-500 text-xs">-</span>
                          )}
                        </td>
                        <td className="py-3">
                          {payment.is_test_mode ? (
                            <span className="px-2 py-1 rounded text-xs font-medium bg-orange-900/50 text-orange-400 border border-orange-700">
                              TEST
                            </span>
                          ) : (
                            <span className="px-2 py-1 rounded text-xs font-medium bg-green-900/50 text-green-400 border border-green-700">
                              LIVE
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
