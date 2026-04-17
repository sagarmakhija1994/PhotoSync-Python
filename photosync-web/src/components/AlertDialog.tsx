import { CheckCircle2, AlertCircle, X } from 'lucide-react';

interface AlertDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  type?: 'success' | 'error';
  onClose: () => void;
}

export default function AlertDialog({ isOpen, title, message, type = 'success', onClose }: AlertDialogProps) {
  if (!isOpen) return null;

  const isSuccess = type === 'success';

  return (
    <div className="fixed inset-0 z-[300] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden transform transition-all text-center p-6 relative">
        
        <button 
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100 transition-colors"
        >
          <X size={20} />
        </button>

        <div className={`w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4 ${isSuccess ? 'bg-emerald-100' : 'bg-red-100'}`}>
          {isSuccess ? (
            <CheckCircle2 size={32} className="text-emerald-600" />
          ) : (
            <AlertCircle size={32} className="text-red-600" />
          )}
        </div>
        
        <h3 className="text-xl font-bold text-slate-900 mb-2">{title}</h3>
        <p className="text-slate-500 mb-6">{message}</p>
        
        <button
          onClick={onClose}
          className={`w-full py-3 px-4 font-medium rounded-xl transition-colors ${
            isSuccess 
              ? 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-md shadow-emerald-600/20' 
              : 'bg-red-600 hover:bg-red-700 text-white shadow-md shadow-red-600/20'
          }`}
        >
          Okay
        </button>
      </div>
    </div>
  );
}