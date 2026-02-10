import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { 
  Car, Search, Calendar, Phone, MapPin, Users, Briefcase, 
  MessageSquare, Download, LogOut, Loader2, Clock, RefreshCw,
  ExternalLink
} from "lucide-react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS_OPTIONS = [
  { value: "nouvelle", label: "Nouvelle", color: "bg-blue-500" },
  { value: "confirmée", label: "Confirmée", color: "bg-green-500" },
  { value: "effectuée", label: "Effectuée", color: "bg-slate-700" },
  { value: "annulée", label: "Annulée", color: "bg-red-500" }
];

const getStatusColor = (status) => {
  const found = STATUS_OPTIONS.find(s => s.value === status);
  return found ? found.color : "bg-slate-500";
};

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [reservations, setReservations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [dateFilter, setDateFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [updatingId, setUpdatingId] = useState(null);

  // Check auth
  useEffect(() => {
    const auth = sessionStorage.getItem("adminAuth");
    if (!auth) {
      navigate("/admin");
    }
  }, [navigate]);

  const fetchReservations = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (search) params.append("search", search);
      if (dateFilter) params.append("date", dateFilter);
      if (statusFilter) params.append("status", statusFilter);
      
      const response = await axios.get(`${API}/reservations?${params.toString()}`);
      setReservations(response.data);
    } catch (error) {
      console.error("Error fetching reservations:", error);
      toast.error("Erreur lors du chargement des réservations");
    } finally {
      setLoading(false);
    }
  }, [search, dateFilter, statusFilter]);

  useEffect(() => {
    fetchReservations();
  }, [fetchReservations]);

  const handleStatusChange = async (id, newStatus) => {
    setUpdatingId(id);
    try {
      await axios.patch(`${API}/reservations/${id}/status`, { status: newStatus });
      setReservations(prev => 
        prev.map(r => r.id === id ? { ...r, status: newStatus } : r)
      );
      toast.success("Statut mis à jour");
    } catch (error) {
      console.error("Error updating status:", error);
      toast.error("Erreur lors de la mise à jour du statut");
    } finally {
      setUpdatingId(null);
    }
  };

  const handleExport = () => {
    const params = new URLSearchParams();
    if (dateFilter) params.append("date", dateFilter);
    if (statusFilter) params.append("status", statusFilter);
    
    window.open(`${API}/reservations/export/csv?${params.toString()}`, '_blank');
    toast.success("Export CSV lancé");
  };

  const handleLogout = () => {
    sessionStorage.removeItem("adminAuth");
    navigate("/admin");
  };

  const openGoogleMaps = (pickup, dropoff) => {
    const url = `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(pickup)}&destination=${encodeURIComponent(dropoff)}`;
    window.open(url, '_blank');
  };

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short' });
  };

  const formatCreatedAt = (isoStr) => {
    const date = new Date(isoStr);
    return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="min-h-screen bg-slate-100">
      {/* Header */}
      <header className="admin-header px-6 py-4 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Car className="w-7 h-7 text-white" />
            <span className="text-xl font-extrabold text-white tracking-tight" style={{ fontFamily: 'Manrope, sans-serif' }}>
              JABADRIVER
            </span>
            <span className="text-sm text-white/50 hidden sm:inline ml-2">Admin</span>
          </div>
          <div className="flex items-center gap-2">
            <Button 
              variant="ghost" 
              size="sm"
              onClick={fetchReservations}
              className="text-white/70 hover:text-white hover:bg-white/10"
              data-testid="refresh-btn"
            >
              <RefreshCw className="w-4 h-4" />
            </Button>
            <Button 
              variant="ghost" 
              size="sm"
              onClick={handleLogout}
              className="text-white/70 hover:text-white hover:bg-white/10"
              data-testid="logout-btn"
            >
              <LogOut className="w-4 h-4 mr-1" />
              <span className="hidden sm:inline">Déconnexion</span>
            </Button>
          </div>
        </div>
      </header>

      {/* Filters */}
      <div className="bg-white border-b border-slate-200 px-6 py-4 sticky top-[64px] z-40">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col sm:flex-row gap-3">
            {/* Search */}
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <Input
                type="text"
                placeholder="Rechercher par nom ou téléphone..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-12 h-12 bg-slate-100 border-transparent focus:border-blue-500 rounded-full"
                data-testid="search-input"
              />
            </div>
            
            {/* Date Filter */}
            <div className="relative">
              <Calendar className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 pointer-events-none" />
              <Input
                type="date"
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value)}
                className="pl-12 h-12 bg-slate-100 border-transparent focus:border-blue-500 rounded-full w-full sm:w-auto"
                data-testid="date-filter"
              />
            </div>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-12 bg-slate-100 border-2 border-transparent focus:border-blue-500 rounded-full px-4 text-slate-700 cursor-pointer"
              data-testid="status-filter"
            >
              <option value="">Tous les statuts</option>
              {STATUS_OPTIONS.map(s => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>

            {/* Export Button */}
            <Button
              onClick={handleExport}
              variant="outline"
              className="h-12 rounded-full px-6 border-2"
              data-testid="export-btn"
            >
              <Download className="w-4 h-4 mr-2" />
              Export CSV
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="px-6 py-6">
        <div className="max-w-6xl mx-auto">
          {/* Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-xl p-4 border border-slate-100">
              <p className="text-sm text-slate-500 mb-1">Total</p>
              <p className="text-2xl font-bold text-slate-900" data-testid="stat-total">
                {reservations.length}
              </p>
            </div>
            <div className="bg-white rounded-xl p-4 border border-slate-100">
              <p className="text-sm text-slate-500 mb-1">Nouvelles</p>
              <p className="text-2xl font-bold text-blue-600" data-testid="stat-new">
                {reservations.filter(r => r.status === "nouvelle").length}
              </p>
            </div>
            <div className="bg-white rounded-xl p-4 border border-slate-100">
              <p className="text-sm text-slate-500 mb-1">Confirmées</p>
              <p className="text-2xl font-bold text-green-600" data-testid="stat-confirmed">
                {reservations.filter(r => r.status === "confirmée").length}
              </p>
            </div>
            <div className="bg-white rounded-xl p-4 border border-slate-100">
              <p className="text-sm text-slate-500 mb-1">Effectuées</p>
              <p className="text-2xl font-bold text-slate-700" data-testid="stat-done">
                {reservations.filter(r => r.status === "effectuée").length}
              </p>
            </div>
          </div>

          {/* Reservations List */}
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 text-slate-400 spinner" />
            </div>
          ) : reservations.length === 0 ? (
            <div className="text-center py-20 bg-white rounded-2xl border border-slate-100">
              <Calendar className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <p className="text-slate-500">Aucune réservation trouvée</p>
            </div>
          ) : (
            <div className="space-y-4" data-testid="reservations-list">
              {reservations.map((reservation, index) => (
                <div 
                  key={reservation.id} 
                  className="reservation-card animate-fadeIn"
                  style={{ animationDelay: `${index * 50}ms` }}
                  data-testid={`reservation-${reservation.id}`}
                >
                  {/* Header */}
                  <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
                    <div>
                      <h3 className="text-lg font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                        {reservation.name}
                      </h3>
                      <p className="text-sm text-slate-500 flex items-center gap-2 mt-1">
                        <Clock className="w-4 h-4" />
                        Créé le {formatCreatedAt(reservation.created_at)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {/* Status Badge */}
                      <span className={`${getStatusColor(reservation.status)} text-white text-xs font-semibold px-3 py-1.5 rounded-full`}>
                        {reservation.status.charAt(0).toUpperCase() + reservation.status.slice(1)}
                      </span>
                    </div>
                  </div>

                  {/* Details Grid */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                    {/* Date & Time */}
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center flex-shrink-0">
                        <Calendar className="w-5 h-5 text-blue-600" />
                      </div>
                      <div>
                        <p className="text-sm text-slate-500">Date & Heure</p>
                        <p className="font-semibold text-slate-900">{formatDate(reservation.date)} à {reservation.time}</p>
                      </div>
                    </div>

                    {/* Passengers */}
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-slate-100 rounded-xl flex items-center justify-center flex-shrink-0">
                        <Users className="w-5 h-5 text-slate-600" />
                      </div>
                      <div>
                        <p className="text-sm text-slate-500">Passagers</p>
                        <p className="font-semibold text-slate-900">{reservation.passengers}</p>
                      </div>
                    </div>

                    {/* Pickup */}
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-green-50 rounded-xl flex items-center justify-center flex-shrink-0">
                        <MapPin className="w-5 h-5 text-green-600" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm text-slate-500">Départ</p>
                        <p className="font-medium text-slate-900 truncate">{reservation.pickup_address}</p>
                      </div>
                    </div>

                    {/* Dropoff */}
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-red-50 rounded-xl flex items-center justify-center flex-shrink-0">
                        <MapPin className="w-5 h-5 text-red-600" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm text-slate-500">Arrivée</p>
                        <p className="font-medium text-slate-900 truncate">{reservation.dropoff_address}</p>
                      </div>
                    </div>
                  </div>

                  {/* Optional Info */}
                  {(reservation.luggage || reservation.notes) && (
                    <div className="flex flex-wrap gap-4 mb-4 pt-4 border-t border-slate-100">
                      {reservation.luggage && (
                        <div className="flex items-center gap-2 text-sm text-slate-600">
                          <Briefcase className="w-4 h-4" />
                          {reservation.luggage}
                        </div>
                      )}
                      {reservation.notes && (
                        <div className="flex items-center gap-2 text-sm text-slate-600">
                          <MessageSquare className="w-4 h-4" />
                          {reservation.notes}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex flex-wrap items-center gap-3 pt-4 border-t border-slate-100">
                    {/* Status Change */}
                    <select
                      value={reservation.status}
                      onChange={(e) => handleStatusChange(reservation.id, e.target.value)}
                      disabled={updatingId === reservation.id}
                      className="h-10 bg-slate-100 border-2 border-transparent focus:border-blue-500 rounded-full px-4 text-sm font-medium cursor-pointer"
                      data-testid={`status-select-${reservation.id}`}
                    >
                      {STATUS_OPTIONS.map(s => (
                        <option key={s.value} value={s.value}>{s.label}</option>
                      ))}
                    </select>

                    {/* Call Button */}
                    <a
                      href={`tel:${reservation.phone}`}
                      className="action-btn bg-green-100 text-green-700 hover:bg-green-200"
                      data-testid={`call-btn-${reservation.id}`}
                    >
                      <Phone className="w-4 h-4" />
                      {reservation.phone}
                    </a>

                    {/* Maps Button */}
                    <button
                      onClick={() => openGoogleMaps(reservation.pickup_address, reservation.dropoff_address)}
                      className="action-btn bg-blue-100 text-blue-700 hover:bg-blue-200"
                      data-testid={`maps-btn-${reservation.id}`}
                    >
                      <ExternalLink className="w-4 h-4" />
                      Itinéraire
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
