import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function PaymentSuccessPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('verifying'); // verifying, paid, failed
  const [message, setMessage] = useState('Vérification du paiement...');
  const [courseId, setCourseId] = useState(null);

  useEffect(() => {
    const sessionId = searchParams.get('session_id');
    const courseIdParam = searchParams.get('course_id');
    
    if (courseIdParam) {
      setCourseId(courseIdParam);
    }
    
    if (sessionId) {
      verifyPayment(sessionId);
    } else {
      setStatus('failed');
      setMessage('Session de paiement non trouvée');
    }
  }, [searchParams]);

  const verifyPayment = async (sessionId) => {
    try {
      console.log('Verifying payment for session:', sessionId);
      
      const res = await fetch(`${API_URL}/api/subcontracting/verify-payment?session_id=${sessionId}`);
      const data = await res.json();
      
      console.log('Verification response:', data);
      
      if (data.success && data.payment_status === 'paid') {
        setStatus('paid');
        setMessage('Paiement confirmé ! La course vous est attribuée.');
        if (data.course_id) {
          setCourseId(data.course_id);
        }
      } else {
        setStatus('failed');
        setMessage(data.message || 'Paiement non confirmé');
      }
    } catch (err) {
      console.error('Verification error:', err);
      setStatus('failed');
      setMessage('Erreur lors de la vérification du paiement');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <Card className="w-full max-w-md bg-slate-800/50 border-slate-700">
        <CardContent className="py-12 text-center">
          {status === 'verifying' && (
            <>
              <Loader2 className="w-16 h-16 text-sky-400 mx-auto mb-4 animate-spin" />
              <h2 className="text-xl text-white mb-2">Vérification en cours</h2>
              <p className="text-slate-400">{message}</p>
            </>
          )}
          
          {status === 'paid' && (
            <>
              <CheckCircle2 className="w-16 h-16 text-green-400 mx-auto mb-4" />
              <h2 className="text-xl text-white mb-2">Paiement réussi !</h2>
              <p className="text-green-400 font-medium mb-4">{message}</p>
              <div className="space-y-3">
                <Button 
                  className="w-full bg-green-600 hover:bg-green-700"
                  onClick={() => navigate('/driver/courses')}
                >
                  Voir mes courses
                </Button>
                {courseId && (
                  <p className="text-slate-500 text-sm">
                    Course ID: {courseId.slice(0, 8)}...
                  </p>
                )}
              </div>
            </>
          )}
          
          {status === 'failed' && (
            <>
              <XCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
              <h2 className="text-xl text-white mb-2">Paiement non confirmé</h2>
              <p className="text-red-400 mb-4">{message}</p>
              <div className="space-y-3">
                <Button 
                  variant="outline"
                  className="w-full border-slate-600 text-slate-300"
                  onClick={() => navigate('/driver/courses')}
                >
                  Voir mes courses
                </Button>
                <Button 
                  variant="ghost"
                  className="w-full text-slate-400"
                  onClick={() => navigate('/')}
                >
                  Retour à l'accueil
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
