import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { 
  FileText, Send, MapPin, Clock, Euro, User, X, AlertTriangle, Loader2,
  Plus, Lock, CheckCircle, Settings, Navigation, Play
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function DriverCoursesPage() {
  const navigate = useNavigate();
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [driverInfo, setDriverInfo] = useState(null);
  
  // Cancel modal state
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelCourseId, setCancelCourseId] = useState(null);
  const [cancelCourse, setCancelCourse] = useState(null);
  const [cancelReason, setCancelReason] = useState('');
  const [cancelling, setCancelling] = useState(false);
  
  // Supplements modal state
  const [showSupplementsModal, setShowSupplementsModal] = useState(false);
  const [supplementsCourseId, setSupplementsCourseId] = useState(null);
  const [supplements, setSupplements] = useState({
    supplement_peage: 0,
    supplement_parking: 0,
    supplement_attente_minutes: 0
  });
  const [savingSupplements, setSavingSupplements] = useState(false);
  
  // Issue invoice state
  const [issuingInvoice, setIssuingInvoice] = useState(null);

  // Set driver manifest for PWA
  useEffect(() => {
    const manifestLink = document.querySelector('link[rel="manifest"]');
    if (manifestLink) manifestLink.href = '/manifest-driver.json?v=5';
    const appleIcon = document.querySelector('link[rel="apple-touch-icon"]');
    if (appleIcon) appleIcon.href = '/icons/driver/apple-touch-icon.png?v=5';
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('driver_token');
    const info = localStorage.getItem('driver_info');
    
    if (!token) {
      navigate('/driver/login');
      return;
    }
    
    if (info) {
      setDriverInfo(JSON.parse(info));
    }
    
    fetchCourses(token);
  }, [navigate]);

  const fetchCourses = async (token, reason = 'init') => {
    try {
      // Cache buster for iOS Safari
      const cacheBuster = `?_t=${Date.now()}`;
      const url = `${API_URL}/api/driver/courses${cacheBuster}`;
      
      console.log(`[COURSES] Fetching courses (${reason}):`, url);
      
      const res = await fetch(url, {
        method: 'GET',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache'
        },
        cache: 'no-store' // Critical for Safari
      });
      
      if (res.status === 401 || res.status === 403) {
        localStorage.removeItem('driver_token');
        localStorage.removeItem('driver_info');
        navigate('/driver/login');
        return;
      }
      
      // Read body ONCE using helper
      const { data } = await safeReadJson(res);
      
      // Debug log: first course status
      if (data && data.length > 0) {
        console.log(`[COURSES] Loaded ${data.length} courses | First: ${data[0].id?.substring(0,8)} status=${data[0].status}`);
      } else {
        console.log(`[COURSES] Loaded 0 courses or empty response`);
      }
      
      setCourses(data || []);
      return data;
    } catch (err) {
      console.error('[COURSES] Fetch error:', err);
      toast.error('Erreur chargement courses');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('driver_token');
    localStorage.removeItem('driver_info');
    navigate('/driver/login');
  };

  // Helper to safely read JSON response body ONCE
  // Returns { ok: boolean, data: object|null, raw: string }
  const safeReadJson = async (res) => {
    try {
      const data = await res.json();
      return { ok: true, data, raw: '' };
    } catch (err) {
      console.error('[FETCH] Body read error:', err.message || err);
      // If JSON parsing fails, return null but mark as readable
      return { ok: false, data: null, raw: '' };
    }
  };

  // Map HTTP status to user-friendly error message
  const getErrorMessage = (status, data) => {
    switch (status) {
      case 409:
        return data?.detail || 'Course déjà démarrée ou terminée';
      case 401:
        return 'Session expirée. Veuillez vous reconnecter.';
      case 403:
        return data?.detail || 'Vous n\'êtes pas assigné à cette course';
      case 404:
        return 'Course non trouvée';
      case 400:
        return data?.detail || 'Action impossible';
      default:
        return data?.detail || `Erreur serveur (${status})`;
    }
  };

  // State for action loading
  const [actionLoading, setActionLoading] = useState(null); // courseId being processed
  
  // Track last action to prevent rapid double-clicks (Safari double-fetch issue)
  const lastActionRef = useRef({ courseId: null, timestamp: 0 });

  // Handle START ride directly from dashboard
  // UX: After successful START, stay in dashboard with updated status (no redirect)
  const handleStartRide = async (courseId, driverAccessToken) => {
    // Debounce: prevent double-click within 2 seconds
    const now = Date.now();
    if (lastActionRef.current.courseId === courseId && now - lastActionRef.current.timestamp < 2000) {
      console.log(`[ACTION] Debounced duplicate START for ${courseId.substring(0,8)}`);
      return;
    }
    lastActionRef.current = { courseId, timestamp: now };
    
    if (actionLoading) {
      console.log(`[ACTION] Already loading, ignoring START for ${courseId.substring(0,8)}`);
      return;
    }
    
    const token = localStorage.getItem('driver_token');
    setActionLoading(courseId);
    
    console.log(`[ACTION] Starting ride ${courseId.substring(0,8)}`);
    
    try {
      // Build URL with token if available, otherwise use session auth
      // Add cache-buster for Safari
      const cacheBuster = `_t=${Date.now()}`;
      const url = driverAccessToken 
        ? `${API_URL}/api/driver/ride/${courseId}/start?token=${driverAccessToken}&${cacheBuster}`
        : `${API_URL}/api/driver/ride/${courseId}/start?${cacheBuster}`;
      
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache'
        },
        cache: 'no-store' // Critical for Safari
      });
      
      // Read body inline - avoid safeReadJson issues with 409 status
      let data = null;
      try {
        data = await res.json();
      } catch (parseErr) {
        console.warn('[ACTION] Failed to parse response JSON:', parseErr.message);
      }
      console.log(`[ACTION] Start response: status=${res.status}`, data);
      
      if (res.status === 401) {
        toast.error('Session expirée. Veuillez vous reconnecter.');
        handleLogout();
        return;
      } else if (res.status === 409) {
        // Course already modified - show current status from response
        const currentStatus = data?.current_status || data?.status;
        const detail = data?.detail || 'Course déjà modifiée';
        const errorCode = data?.error || 'unknown';
        
        console.log(`[ACTION] 409 Conflict | error=${errorCode} | detail=${detail} | current_status=${currentStatus || 'not_provided'} | ride_id=${data?.ride_id || 'N/A'}`);
        
        // Show appropriate message based on status
        if (currentStatus === 'IN_PROGRESS') {
          toast.info('Course déjà en cours - actualisation...');
        } else if (currentStatus === 'DRIVER_COMPLETED') {
          toast.info('Course déjà terminée par le chauffeur');
        } else if (currentStatus === 'DONE') {
          toast.info('Course déjà clôturée');
        } else {
          toast.info(detail);
        }
      } else if (!res.ok) {
        toast.error(getErrorMessage(res.status, data));
        return;
      } else {
        // SUCCESS: Backend returns { success: true, status: "IN_PROGRESS", message: "...", idempotent?: true }
        const newStatus = data?.status || 'IN_PROGRESS';
        const isIdempotent = data?.idempotent === true;
        console.log(`[ACTION] ✅ Start SUCCESS - New status: ${newStatus} | idempotent: ${isIdempotent}`);
        
        // Show appropriate toast based on whether this was a new start or idempotent
        if (isIdempotent) {
          toast.info(data?.message || 'Course déjà en cours');
        } else {
          toast.success(data?.message || 'Course démarrée !');
        }
      }
      
      // Force refetch to update UI (critical: must update badge to IN_PROGRESS)
      console.log('[ACTION] Refetching courses after start...');
      await fetchCourses(token, 'after-start');
      
    } catch (err) {
      console.error('[ACTION] Start error:', err);
      toast.error(`Erreur réseau: ${err.message || 'Connexion impossible'}`);
    } finally {
      setActionLoading(null);
    }
  };

  // Handle END ride directly from dashboard
  // UX: After successful END, stay in dashboard with status DRIVER_COMPLETED
  const handleEndRide = async (courseId, driverAccessToken) => {
    // Debounce: prevent double-click within 2 seconds
    const now = Date.now();
    if (lastActionRef.current.courseId === courseId && now - lastActionRef.current.timestamp < 2000) {
      console.log(`[ACTION] Debounced duplicate END for ${courseId.substring(0,8)}`);
      return;
    }
    lastActionRef.current = { courseId, timestamp: now };
    
    if (actionLoading) {
      console.log(`[ACTION] Already loading, ignoring END for ${courseId.substring(0,8)}`);
      return;
    }
    
    const token = localStorage.getItem('driver_token');
    setActionLoading(courseId);
    
    console.log(`[ACTION] Ending ride ${courseId.substring(0,8)}`);
    
    try {
      // Build URL with token if available, otherwise use session auth
      // Add cache-buster for Safari
      const cacheBuster = `_t=${Date.now()}`;
      const url = driverAccessToken 
        ? `${API_URL}/api/driver/ride/${courseId}/end?token=${driverAccessToken}&${cacheBuster}`
        : `${API_URL}/api/driver/ride/${courseId}/end?${cacheBuster}`;
      
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache'
        },
        cache: 'no-store' // Critical for Safari
      });
      
      // Read body inline - avoid safeReadJson issues with 409 status
      let data = null;
      try {
        data = await res.json();
      } catch (parseErr) {
        console.warn('[ACTION] Failed to parse response JSON:', parseErr.message);
      }
      console.log(`[ACTION] End response: status=${res.status}`, data);
      
      if (res.status === 401) {
        toast.error('Session expirée. Veuillez vous reconnecter.');
        handleLogout();
        return;
      } else if (res.status === 409) {
        // Course already modified - show current status from response
        const currentStatus = data?.current_status || data?.status;
        const errorCode = data?.error || 'unknown';
        console.log(`[ACTION] 409 Conflict | error=${errorCode} | current_status=${currentStatus}`);
        
        // Show appropriate message based on status
        if (currentStatus === 'DRIVER_COMPLETED') {
          toast.info('Course déjà terminée - actualisation...');
        } else if (currentStatus === 'DONE') {
          toast.info('Course déjà clôturée par le client');
        } else {
          toast.info(data?.detail || 'La course a déjà été modifiée');
        }
      } else if (!res.ok) {
        toast.error(getErrorMessage(res.status, data));
        return;
      } else {
        // SUCCESS: Backend returns { success: true, status: "DRIVER_COMPLETED", message: "..." }
        const newStatus = data?.status || 'DRIVER_COMPLETED';
        console.log(`[ACTION] ✅ End SUCCESS - New status: ${newStatus}`);
        toast.success(data?.message || 'Course terminée !');
      }
      
      // Force refetch to update UI
      console.log('[ACTION] Refetching courses after end...');
      await fetchCourses(token, 'after-end');
      
    } catch (err) {
      console.error('[ACTION] End error:', err);
      toast.error(`Erreur réseau: ${err.message || 'Connexion impossible'}`);
    } finally {
      setActionLoading(null);
    }
  };

  const downloadPDF = async (courseId, type) => {
    const token = localStorage.getItem('driver_token');
    try {
      const endpoint = type === 'bon' 
        ? `${API_URL}/api/driver/courses/${courseId}/bon-commande-pdf`
        : `${API_URL}/api/driver/courses/${courseId}/invoice-pdf`;
      
      const res = await fetch(endpoint, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!res.ok) throw new Error('Erreur téléchargement');
      
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = type === 'bon' ? `bon_commande_${courseId.slice(0,8)}.pdf` : `facture_${courseId.slice(0,8)}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success('PDF téléchargé');
    } catch (err) {
      toast.error(err.message);
    }
  };

  const sendInvoice = async (courseId) => {
    const token = localStorage.getItem('driver_token');
    try {
      const res = await fetch(`${API_URL}/api/driver/courses/${courseId}/send-invoice`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      const data = await res.json();
      
      if (!res.ok) throw new Error(data.detail || 'Erreur envoi');
      
      toast.success(data.message);
      // Refresh to update invoice status
      fetchCourses(token);
    } catch (err) {
      toast.error(err.message);
    }
  };

  // Issue/freeze invoice
  const handleIssueInvoice = async (courseId) => {
    const token = localStorage.getItem('driver_token');
    setIssuingInvoice(courseId);
    
    try {
      const res = await fetch(`${API_URL}/api/driver/courses/${courseId}/issue-invoice`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      const data = await res.json();
      
      if (!res.ok) throw new Error(data.detail || 'Erreur émission facture');
      
      toast.success(data.message);
      // Refresh to update invoice status
      fetchCourses(token);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setIssuingInvoice(null);
    }
  };

  // Open supplements modal
  const openSupplementsModal = async (course) => {
    setSupplementsCourseId(course.id);
    setSupplements({
      supplement_peage: course.supplement_peage || 0,
      supplement_parking: course.supplement_parking || 0,
      supplement_attente_minutes: course.supplement_attente_minutes || 0
    });
    setShowSupplementsModal(true);
  };

  // Save supplements
  const handleSaveSupplements = async () => {
    const token = localStorage.getItem('driver_token');
    setSavingSupplements(true);
    
    try {
      const res = await fetch(`${API_URL}/api/driver/courses/${supplementsCourseId}/supplements`, {
        method: 'PATCH',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(supplements)
      });
      
      const data = await res.json();
      
      if (!res.ok) throw new Error(data.detail || 'Erreur mise à jour');
      
      toast.success('Suppléments mis à jour');
      setShowSupplementsModal(false);
      // Refresh courses
      fetchCourses(token);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSavingSupplements(false);
    }
  };

  // Check if course is < 1h before pickup
  const isLessThanOneHour = (course) => {
    try {
      const pickupDateTime = new Date(`${course.date}T${course.time}`);
      const now = new Date();
      const diffMs = pickupDateTime - now;
      return diffMs < 3600000;
    } catch {
      return false;
    }
  };

  // Open cancel modal
  const openCancelModal = (course) => {
    setCancelCourseId(course.id);
    setCancelCourse(course);
    setCancelReason('');
    setShowCancelModal(true);
  };

  // Handle cancel course
  const handleCancelCourse = async () => {
    if (!cancelCourseId) return;
    
    const token = localStorage.getItem('driver_token');
    setCancelling(true);
    
    try {
      const res = await fetch(`${API_URL}/api/driver/courses/${cancelCourseId}/cancel?reason=${encodeURIComponent(cancelReason)}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || 'Erreur annulation');
      }
      
      setShowCancelModal(false);
      setCancelCourseId(null);
      setCancelCourse(null);
      setCancelReason('');
      
      if (data.auto_deactivated) {
        toast.error('🚫 Compte désactivé après 3 annulations tardives. Contactez l\'admin.');
        handleLogout();
      } else if (data.is_late_cancellation) {
        toast.warning(`Course annulée. ⚠️ Annulation tardive comptabilisée (${data.late_cancellation_count}/3)`);
      } else {
        toast.success('Course annulée, emails envoyés.');
      }
      
      fetchCourses(token);
      
    } catch (err) {
      toast.error(err.message);
    } finally {
      setCancelling(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'ASSIGNED': return 'bg-sky-500/20 text-sky-400 border-sky-500/30';
      case 'IN_PROGRESS': return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'DRIVER_COMPLETED': return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'DONE': return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
      case 'CANCELLED': return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'CANCELLED_LATE_DRIVER': return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'CANCELLED_LATE_CLIENT': return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'ASSIGNED': return 'Attribuée';
      case 'IN_PROGRESS': return 'En cours';
      case 'DRIVER_COMPLETED': return 'Terminée (attente client)';
      case 'DONE': return 'Terminée';
      case 'CANCELLED': return 'Annulée';
      case 'CANCELLED_LATE_DRIVER': return 'Annulée (chauffeur)';
      case 'CANCELLED_LATE_CLIENT': return 'Annulée (client)';
      default: return status;
    }
  };

  // Check if course can use ride workflow
  const canUseRideWorkflow = (course) => {
    // Allow workflow for active statuses - works with session auth or token
    return ['ASSIGNED', 'IN_PROGRESS', 'DRIVER_COMPLETED'].includes(course.status);
  };

  // Get ride workflow button config based on status
  const getRideWorkflowConfig = (status) => {
    switch(status) {
      case 'ASSIGNED': 
        return { 
          label: 'Démarrer la course', 
          icon: Play, 
          className: 'bg-amber-500 hover:bg-amber-600 text-black',
          action: 'start'
        };
      case 'IN_PROGRESS': 
        return { 
          label: 'Terminer la course', 
          icon: CheckCircle, 
          className: 'bg-green-500 hover:bg-green-600 text-white',
          action: 'end'
        };
      case 'DRIVER_COMPLETED': 
        return { 
          label: 'Attente confirmation', 
          icon: Clock, 
          className: 'bg-gray-600 text-white cursor-default',
          action: 'none'
        };
      default: 
        return { 
          label: 'Voir', 
          icon: Navigation, 
          className: 'bg-slate-600 hover:bg-slate-700 text-white',
          action: 'view'
        };
    }
  };

  // Calculate total with supplements
  const calculateTotal = (course) => {
    const base = course.price_base || course.price_total || 0;
    const peage = course.supplement_peage || 0;
    const parking = course.supplement_parking || 0;
    const attente = course.supplement_attente_amount || 0;
    return base + peage + parking + attente;
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
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white">Mes Courses</h1>
            {driverInfo && (
              <p className="text-slate-400">{driverInfo.company_name}</p>
            )}
          </div>
          <div className="flex gap-2">
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => navigate('/driver/profile')}
              className="border-slate-600 text-slate-300"
            >
              Mon Profil
            </Button>
            <Button 
              variant="ghost" 
              size="sm"
              onClick={handleLogout}
              className="text-slate-400 hover:text-white"
            >
              Déconnexion
            </Button>
          </div>
        </div>

        {/* Courses List */}
        {courses.length === 0 ? (
          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="py-12 text-center">
              <p className="text-slate-400">Aucune course attribuée pour le moment.</p>
              <p className="text-slate-500 text-sm mt-2">
                Les courses vous seront attribuées après paiement de la commission.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {courses.map((course) => {
              const isInvoiceIssued = course.invoice_status === 'ISSUED';
              const totalWithSupplements = calculateTotal(course);
              
              return (
                <Card key={course.id} className="bg-slate-800/50 border-slate-700" data-testid={`course-card-${course.id}`}>
                  <CardContent className="p-4">
                    <div className="flex justify-between items-start mb-3">
                      <div className="flex items-center gap-2">
                        <User className="w-4 h-4 text-slate-400" />
                        <span className="text-white font-medium">{course.client_name}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        {/* Invoice status badge */}
                        {isInvoiceIssued ? (
                          <span className="px-2 py-1 rounded text-xs bg-green-500/20 text-green-400 border border-green-500/30 flex items-center gap-1">
                            <Lock className="w-3 h-3" />
                            Facture {course.invoice_number}
                          </span>
                        ) : (
                          <span className="px-2 py-1 rounded text-xs bg-amber-500/20 text-amber-400 border border-amber-500/30">
                            Brouillon
                          </span>
                        )}
                        <span className={`px-2 py-1 rounded text-xs border ${getStatusColor(course.status)}`}>
                          {getStatusLabel(course.status)}
                        </span>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
                      <div className="flex items-start gap-2">
                        <MapPin className="w-4 h-4 text-green-400 mt-0.5" />
                        <div>
                          <p className="text-xs text-slate-500">Départ</p>
                          <p className="text-slate-300 text-sm">{course.pickup_address}</p>
                        </div>
                      </div>
                      <div className="flex items-start gap-2">
                        <MapPin className="w-4 h-4 text-red-400 mt-0.5" />
                        <div>
                          <p className="text-xs text-slate-500">Arrivée</p>
                          <p className="text-slate-300 text-sm">{course.dropoff_address}</p>
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-4 mb-4 text-sm">
                      <div className="flex items-center gap-1 text-slate-400">
                        <Clock className="w-4 h-4" />
                        {course.date} à {course.time}
                      </div>
                      <div className="flex items-center gap-1 text-sky-400 font-medium">
                        <Euro className="w-4 h-4" />
                        {totalWithSupplements.toFixed(2)} €
                        {(course.supplement_peage > 0 || course.supplement_parking > 0 || course.supplement_attente_amount > 0) && (
                          <span className="text-xs text-slate-500 ml-1">
                            (base: {(course.price_base || course.price_total || 0).toFixed(2)}€)
                          </span>
                        )}
                      </div>
                    </div>
                    
                    {/* Supplements summary if any */}
                    {(course.supplement_peage > 0 || course.supplement_parking > 0 || course.supplement_attente_amount > 0) && (
                      <div className="bg-slate-700/50 rounded p-2 mb-3 text-xs text-slate-400">
                        <span className="font-medium">Suppléments:</span>
                        {course.supplement_peage > 0 && <span className="ml-2">Péage: {course.supplement_peage}€</span>}
                        {course.supplement_parking > 0 && <span className="ml-2">Parking: {course.supplement_parking}€</span>}
                        {course.supplement_attente_amount > 0 && (
                          <span className="ml-2">Attente ({course.supplement_attente_minutes}min): {course.supplement_attente_amount}€</span>
                        )}
                      </div>
                    )}
                    
                    {/* Actions */}
                    <div className="flex flex-wrap gap-2 pt-3 border-t border-slate-700">
                      {/* RIDE WORKFLOW BUTTON - Primary action for active rides */}
                      {canUseRideWorkflow(course) && (() => {
                        const config = getRideWorkflowConfig(course.status);
                        const IconComponent = config.icon;
                        const isLoading = actionLoading === course.id;
                        
                        // Determine click handler based on action type
                        const handleClick = () => {
                          console.log(`[BUTTON] Clicked ${config.action} for course ${course.id.substring(0,8)}`);
                          if (config.action === 'start') {
                            handleStartRide(course.id, course.driver_access_token);
                          } else if (config.action === 'end') {
                            handleEndRide(course.id, course.driver_access_token);
                          } else if (config.action === 'view' && course.driver_access_token) {
                            navigate(`/driver/ride/${course.id}?token=${course.driver_access_token}`);
                          }
                          // 'none' action does nothing (DRIVER_COMPLETED waiting for client)
                        };
                        
                        return (
                          <Button
                            size="sm"
                            className={`${config.className} font-semibold ${isLoading ? 'opacity-75' : ''}`}
                            onClick={handleClick}
                            disabled={isLoading || config.action === 'none'}
                            data-testid={`ride-workflow-${course.id}`}
                          >
                            {isLoading ? (
                              <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                            ) : (
                              <IconComponent className="w-4 h-4 mr-1" />
                            )}
                            {isLoading ? 'En cours...' : config.label}
                          </Button>
                        );
                      })()}
                      
                      {/* Supplements button - only if invoice not issued and ASSIGNED */}
                      {!isInvoiceIssued && course.status === 'ASSIGNED' && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="border-amber-600/50 text-amber-400 hover:bg-amber-900/30"
                          onClick={() => openSupplementsModal(course)}
                          data-testid={`supplements-${course.id}`}
                        >
                          <Plus className="w-4 h-4 mr-1" />
                          Suppléments
                        </Button>
                      )}
                      
                      <Button
                        size="sm"
                        variant="outline"
                        className="border-slate-600 text-slate-300 hover:bg-slate-700"
                        onClick={() => downloadPDF(course.id, 'bon')}
                        data-testid={`download-bon-${course.id}`}
                      >
                        <FileText className="w-4 h-4 mr-1" />
                        Bon de commande
                      </Button>
                      
                      <Button
                        size="sm"
                        variant="outline"
                        className="border-slate-600 text-slate-300 hover:bg-slate-700"
                        onClick={() => downloadPDF(course.id, 'facture')}
                        data-testid={`download-invoice-${course.id}`}
                      >
                        <FileText className="w-4 h-4 mr-1" />
                        {isInvoiceIssued ? `Facture ${course.invoice_number}` : 'Aperçu facture'}
                      </Button>
                      
                      {/* Issue invoice button - only if DRAFT */}
                      {!isInvoiceIssued && course.status === 'ASSIGNED' && (
                        <Button
                          size="sm"
                          className="bg-green-600 hover:bg-green-700"
                          onClick={() => handleIssueInvoice(course.id)}
                          disabled={issuingInvoice === course.id}
                          data-testid={`issue-invoice-${course.id}`}
                        >
                          {issuingInvoice === course.id ? (
                            <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                          ) : (
                            <CheckCircle className="w-4 h-4 mr-1" />
                          )}
                          Émettre facture
                        </Button>
                      )}
                      
                      {/* Send invoice - only if ISSUED */}
                      {isInvoiceIssued && (
                        <Button
                          size="sm"
                          className="bg-sky-600 hover:bg-sky-700"
                          onClick={() => sendInvoice(course.id)}
                          data-testid={`send-invoice-${course.id}`}
                        >
                          <Send className="w-4 h-4 mr-1" />
                          Envoyer facture
                        </Button>
                      )}
                      
                      {/* Cancel button - only for ASSIGNED courses and invoice not issued */}
                      {course.status === 'ASSIGNED' && !isInvoiceIssued && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="border-red-600/50 text-red-400 hover:bg-red-900/30"
                          onClick={() => openCancelModal(course)}
                          data-testid={`cancel-course-${course.id}`}
                        >
                          <X className="w-4 h-4 mr-1" />
                          Annuler
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Supplements Modal */}
      {showSupplementsModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="bg-slate-800 border border-slate-700 rounded-lg w-full max-w-md p-6">
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <Settings className="w-5 h-5 text-amber-400" />
              Ajouter des suppléments
            </h3>
            
            <div className="space-y-4">
              <div>
                <Label className="text-slate-300 text-sm">Supplément péage (€)</Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  value={supplements.supplement_peage}
                  onChange={(e) => setSupplements({...supplements, supplement_peage: parseFloat(e.target.value) || 0})}
                  className="bg-slate-700 border-slate-600 text-white"
                  placeholder="Ex: 12.50"
                  data-testid="supplement-peage-input"
                />
              </div>
              
              <div>
                <Label className="text-slate-300 text-sm">Supplément parking (€)</Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  value={supplements.supplement_parking}
                  onChange={(e) => setSupplements({...supplements, supplement_parking: parseFloat(e.target.value) || 0})}
                  className="bg-slate-700 border-slate-600 text-white"
                  placeholder="Ex: 5.00"
                  data-testid="supplement-parking-input"
                />
              </div>
              
              <div>
                <Label className="text-slate-300 text-sm">Temps d'attente (minutes)</Label>
                <Input
                  type="number"
                  min="0"
                  value={supplements.supplement_attente_minutes}
                  onChange={(e) => setSupplements({...supplements, supplement_attente_minutes: parseInt(e.target.value) || 0})}
                  className="bg-slate-700 border-slate-600 text-white"
                  placeholder="Ex: 15"
                  data-testid="supplement-attente-input"
                />
                <p className="text-xs text-slate-500 mt-1">Calcul automatique: 0,50€/minute</p>
              </div>
              
              {/* Preview total */}
              <div className="bg-slate-700/50 rounded p-3">
                <p className="text-slate-400 text-sm">Supplément attente estimé:</p>
                <p className="text-amber-400 font-medium">{(supplements.supplement_attente_minutes * 0.5).toFixed(2)} €</p>
              </div>
            </div>
            
            <div className="flex gap-2 mt-6">
              <Button
                onClick={handleSaveSupplements}
                disabled={savingSupplements}
                className="flex-1 bg-amber-600 hover:bg-amber-700"
                data-testid="save-supplements-btn"
              >
                {savingSupplements ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Enregistrement...
                  </>
                ) : (
                  'Enregistrer'
                )}
              </Button>
              <Button
                variant="outline"
                onClick={() => setShowSupplementsModal(false)}
                disabled={savingSupplements}
                className="border-slate-600 text-slate-300"
              >
                Annuler
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Cancel Confirmation Modal */}
      {showCancelModal && cancelCourse && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="bg-slate-800 border border-slate-700 rounded-lg w-full max-w-md p-6">
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <X className="w-5 h-5 text-red-400" />
              Annuler cette course ?
            </h3>
            
            {/* Late cancellation warning */}
            {isLessThanOneHour(cancelCourse) && (
              <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 mb-4">
                <p className="text-red-400 text-sm flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <span>
                    <strong>⚠️ Annulation &lt; 1h = comptabilisée.</strong><br/>
                    Au bout de 3 annulations tardives : désactivation automatique du compte.
                  </span>
                </p>
              </div>
            )}
            
            <div className="mb-4">
              <p className="text-slate-300 text-sm mb-2">
                <strong>Course :</strong> {cancelCourse.date} à {cancelCourse.time}
              </p>
              <p className="text-slate-400 text-sm">
                {cancelCourse.pickup_address?.slice(0, 40)}...
              </p>
            </div>
            
            <div className="mb-4">
              <label className="text-slate-400 text-sm block mb-1">Motif (optionnel)</label>
              <textarea
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                placeholder="Raison de l'annulation..."
                className="w-full p-2 bg-slate-700 border border-slate-600 rounded text-white text-sm resize-none h-20"
              />
            </div>
            
            <div className="flex gap-2">
              <Button
                onClick={handleCancelCourse}
                disabled={cancelling}
                className="flex-1 bg-red-600 hover:bg-red-700"
                data-testid="confirm-cancel-btn"
              >
                {cancelling ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Annulation...
                  </>
                ) : (
                  'Confirmer l\'annulation'
                )}
              </Button>
              <Button
                variant="outline"
                onClick={() => setShowCancelModal(false)}
                disabled={cancelling}
                className="border-slate-600 text-slate-300"
              >
                Retour
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
