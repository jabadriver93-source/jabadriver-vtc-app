import { useState, useEffect } from "react";
import { X, FileText, Download, Send, Loader2, Euro, AlertCircle, Plane } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function InvoiceModal({ reservation, onClose, onInvoiceGenerated }) {
  const [basePrice, setBasePrice] = useState(
    reservation.base_price || reservation.estimated_price || 10
  );
  const [isAirportTrip, setIsAirportTrip] = useState(reservation.is_airport_trip || false);
  const [airportSurcharge, setAirportSurcharge] = useState(reservation.airport_surcharge || 10);
  const [finalPrice, setFinalPrice] = useState(
    reservation.final_price || reservation.estimated_price || 10
  );
  const [invoiceDetails, setInvoiceDetails] = useState(reservation.invoice_details || "");
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [updatingSurcharge, setUpdatingSurcharge] = useState(false);
  
  const isInvoiceGenerated = reservation.invoice_generated;
  
  // Recalculate total price when airport surcharge changes
  useEffect(() => {
    const calculatedTotal = parseFloat(basePrice) + (isAirportTrip ? parseFloat(airportSurcharge) : 0);
    setFinalPrice(calculatedTotal);
  }, [basePrice, isAirportTrip, airportSurcharge]);
  
  const handleUpdateAirportSurcharge = async () => {
    setUpdatingSurcharge(true);
    try {
      const response = await axios.patch(`${API}/reservations/${reservation.id}/airport-surcharge`, {
        is_airport_trip: isAirportTrip,
        airport_surcharge: isAirportTrip ? parseFloat(airportSurcharge) : 0
      });
      
      toast.success("Supplément aéroport mis à jour");
      
      // Update reservation data
      if (onInvoiceGenerated) {
        onInvoiceGenerated(reservation.id, {
          is_airport_trip: response.data.is_airport_trip,
          airport_surcharge: response.data.airport_surcharge,
          estimated_price: response.data.estimated_price
        });
      }
    } catch (error) {
      console.error("Error updating airport surcharge:", error);
      toast.error("Erreur lors de la mise à jour du supplément");
    } finally {
      setUpdatingSurcharge(false);
    }
  };
  
  const handleGenerateInvoice = async () => {
    if (finalPrice < 10) {
      toast.error("Le prix minimum est de 10€");
      return;
    }
    
    setLoading(true);
    try {
      const response = await axios.post(`${API}/reservations/${reservation.id}/invoice`, {
        final_price: parseFloat(finalPrice),
        invoice_details: invoiceDetails || null
      });
      
      toast.success(`Facture ${response.data.invoice_number} générée`);
      onInvoiceGenerated(reservation.id, {
        invoice_number: response.data.invoice_number,
        invoice_date: response.data.invoice_date,
        final_price: parseFloat(finalPrice),
        invoice_details: invoiceDetails,
        invoice_generated: true
      });
    } catch (error) {
      console.error("Error generating invoice:", error);
      toast.error(error.response?.data?.detail || "Erreur lors de la génération");
    } finally {
      setLoading(false);
    }
  };
  
  const handleDownloadPDF = () => {
    window.open(`${API}/reservations/${reservation.id}/invoice/pdf`, '_blank');
    toast.success("Téléchargement du PDF");
  };
  
  const handleSendEmail = async () => {
    if (!reservation.email) {
      toast.error("Email client non renseigné");
      return;
    }
    
    setSending(true);
    try {
      await axios.post(`${API}/reservations/${reservation.id}/invoice/send`);
      toast.success(`Facture envoyée à ${reservation.email}`);
    } catch (error) {
      console.error("Error sending invoice:", error);
      toast.error(error.response?.data?.detail || "Erreur lors de l'envoi");
    } finally {
      setSending(false);
    }
  };
  
  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto" data-testid="invoice-modal">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-[#7dd3fc]/20 rounded-xl flex items-center justify-center">
              <FileText className="w-5 h-5 text-[#0ea5e9]" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                Facture
              </h2>
              {isInvoiceGenerated && (
                <p className="text-sm text-slate-500">N° {reservation.invoice_number}</p>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
            data-testid="close-invoice-modal"
          >
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>
        
        {/* Content */}
        <div className="p-5 space-y-5">
          {/* Client Info */}
          <div className="bg-slate-50 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">Client</h3>
            <p className="font-semibold text-slate-900">{reservation.name}</p>
            <p className="text-slate-600">{reservation.phone}</p>
            {reservation.email && (
              <p className="text-slate-600">{reservation.email}</p>
            )}
          </div>
          
          {/* Course Info */}
          <div className="bg-slate-50 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">Course</h3>
            <div className="space-y-2 text-sm">
              <p><span className="text-slate-500">Date:</span> <span className="text-slate-900 font-medium">{reservation.date} à {reservation.time}</span></p>
              <p><span className="text-slate-500">Départ:</span> <span className="text-slate-900">{reservation.pickup_address}</span></p>
              <p><span className="text-slate-500">Arrivée:</span> <span className="text-slate-900">{reservation.dropoff_address}</span></p>
              {(reservation.distance_km || reservation.duration_min) && (
                <p>
                  <span className="text-slate-500">Distance/Durée:</span>{' '}
                  <span className="text-slate-900">
                    {reservation.distance_km && `${reservation.distance_km} km`}
                    {reservation.distance_km && reservation.duration_min && ' • '}
                    {reservation.duration_min && `${Math.round(reservation.duration_min)} min`}
                  </span>
                </p>
              )}
              <p><span className="text-slate-500">Référence:</span> <span className="text-slate-900 font-mono">#{reservation.id.slice(0, 8).toUpperCase()}</span></p>
            </div>
          </div>
          
          {/* Airport Surcharge Section */}
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
            <div className="flex items-start justify-between gap-4 mb-3">
              <div className="flex items-center gap-2">
                <Plane className="w-5 h-5 text-amber-600" />
                <div>
                  <h3 className="text-sm font-semibold text-amber-900">Supplément aéroport</h3>
                  <p className="text-xs text-amber-700 mt-0.5">
                    Détecté: {reservation.is_airport_trip ? 'Oui ✈️' : 'Non'}
                  </p>
                </div>
              </div>
              
              {/* Toggle */}
              <button
                onClick={() => setIsAirportTrip(!isAirportTrip)}
                disabled={isInvoiceGenerated}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  isAirportTrip ? 'bg-amber-600' : 'bg-slate-300'
                } ${isInvoiceGenerated ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                data-testid="airport-surcharge-toggle"
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    isAirportTrip ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
            
            {isAirportTrip && (
              <div className="space-y-2">
                <label className="block text-xs font-semibold text-amber-900">
                  Montant du supplément (€)
                </label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    min="0"
                    step="1"
                    value={airportSurcharge}
                    onChange={(e) => setAirportSurcharge(e.target.value)}
                    disabled={isInvoiceGenerated}
                    className={`flex-1 h-10 px-3 rounded-lg border-2 ${
                      isInvoiceGenerated 
                        ? 'bg-amber-50 border-amber-200 text-amber-500' 
                        : 'bg-white border-amber-300 focus:border-amber-500 text-slate-900'
                    } outline-none transition-colors`}
                    data-testid="airport-surcharge-amount"
                  />
                  <button
                    onClick={handleUpdateAirportSurcharge}
                    disabled={updatingSurcharge || isInvoiceGenerated}
                    className="px-4 h-10 bg-amber-600 text-white rounded-lg font-semibold hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
                  >
                    {updatingSurcharge ? 'Mise à jour...' : 'Appliquer'}
                  </button>
                </div>
              </div>
            )}
          </div>
          
          {/* Price Breakdown */}
          <div className="bg-slate-50 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">Calcul du prix</h3>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-slate-600">Prix de base:</span>
                <span className="font-semibold text-slate-900">{parseFloat(basePrice).toFixed(2)}€</span>
              </div>
              {isAirportTrip && (
                <div className="flex justify-between text-sm">
                  <span className="text-amber-700">Supplément aéroport:</span>
                  <span className="font-semibold text-amber-700">+ {parseFloat(airportSurcharge).toFixed(2)}€</span>
                </div>
              )}
              <div className="flex justify-between text-base pt-2 border-t border-slate-200">
                <span className="font-bold text-slate-900">TOTAL:</span>
                <span className="font-bold text-[#0ea5e9] text-lg">{finalPrice.toFixed(2)}€</span>
              </div>
            </div>
          </div>
          
          {/* Price Input - Keep for invoice generation */}
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Prix final pour facture (€) *
            </label>
            <div className="relative">
              <input
                type="number"
                min="10"
                step="0.01"
                value={finalPrice}
                onChange={(e) => setFinalPrice(e.target.value)}
                disabled={isInvoiceGenerated}
                className={`w-full h-14 pl-12 pr-4 text-lg font-bold rounded-xl border-2 ${
                  isInvoiceGenerated 
                    ? 'bg-slate-100 border-slate-200 text-slate-500' 
                    : 'bg-white border-slate-200 focus:border-[#7dd3fc] text-slate-900'
                } outline-none transition-colors`}
                data-testid="invoice-final-price"
              />
              <Euro className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Prix calculé automatiquement. Vous pouvez le modifier manuellement si nécessaire.
            </p>
          </div>
          
          {/* Details Input */}
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Détails / Suppléments (optionnel)
            </label>
            <textarea
              value={invoiceDetails}
              onChange={(e) => setInvoiceDetails(e.target.value)}
              disabled={isInvoiceGenerated}
              placeholder="Ex: Péages, temps d'attente, bagages supplémentaires..."
              className={`w-full h-24 p-4 rounded-xl border-2 resize-none ${
                isInvoiceGenerated 
                  ? 'bg-slate-100 border-slate-200 text-slate-500' 
                  : 'bg-white border-slate-200 focus:border-[#7dd3fc] text-slate-900'
              } outline-none transition-colors placeholder:text-slate-400`}
              data-testid="invoice-details"
            />
          </div>
          
          {/* TVA Notice */}
          <div className="flex items-start gap-2 p-3 bg-amber-50 rounded-xl">
            <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-amber-800">
              TVA non applicable – art. 293 B du CGI
            </p>
          </div>
        </div>
        
        {/* Actions */}
        <div className="p-5 border-t border-slate-100 space-y-3">
          {!isInvoiceGenerated ? (
            <button
              onClick={handleGenerateInvoice}
              disabled={loading || finalPrice < 10}
              className="w-full h-12 bg-[#0a0a0a] hover:bg-[#1a1a1a] text-white rounded-xl font-semibold flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="generate-invoice-btn"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 spinner" />
                  Génération...
                </>
              ) : (
                <>
                  <FileText className="w-5 h-5" />
                  Générer la facture
                </>
              )}
            </button>
          ) : (
            <>
              <button
                onClick={handleDownloadPDF}
                className="w-full h-12 bg-[#0a0a0a] hover:bg-[#1a1a1a] text-white rounded-xl font-semibold flex items-center justify-center gap-2 transition-colors"
                data-testid="download-invoice-btn"
              >
                <Download className="w-5 h-5" />
                Télécharger le PDF
              </button>
              
              {reservation.email && (
                <button
                  onClick={handleSendEmail}
                  disabled={sending}
                  className="w-full h-12 bg-[#7dd3fc] hover:bg-[#5bc4f7] text-[#0a0a0a] rounded-xl font-semibold flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                  data-testid="send-invoice-btn"
                >
                  {sending ? (
                    <>
                      <Loader2 className="w-5 h-5 spinner" />
                      Envoi en cours...
                    </>
                  ) : (
                    <>
                      <Send className="w-5 h-5" />
                      Envoyer au client ({reservation.email})
                    </>
                  )}
                </button>
              )}
              
              {!reservation.email && (
                <p className="text-center text-sm text-slate-500">
                  Email client non renseigné - envoi impossible
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
