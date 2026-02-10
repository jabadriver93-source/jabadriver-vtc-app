import { useState } from "react";
import { X, FileText, Download, Send, Loader2, Euro, AlertCircle } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function InvoiceModal({ reservation, onClose, onInvoiceGenerated }) {
  const [finalPrice, setFinalPrice] = useState(
    reservation.final_price || reservation.estimated_price || 10
  );
  const [invoiceDetails, setInvoiceDetails] = useState(reservation.invoice_details || "");
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  
  const isInvoiceGenerated = reservation.invoice_generated;
  
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
          
          {/* Price Input */}
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Prix final (€) *
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
            {reservation.estimated_price && (
              <p className="text-xs text-slate-500 mt-1">
                Prix estimé: {reservation.estimated_price}€
              </p>
            )}
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
