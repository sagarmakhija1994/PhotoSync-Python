import { useState } from 'react';
import { X, Trash2 } from 'lucide-react';

interface DeleteAlbumDialogProps {
  isOpen: boolean;
  albumName: string;
  onClose: () => void;
  onConfirm: (deleteFiles: boolean) => void;
  isProcessing: boolean;
}

export default function DeleteAlbumDialog({ isOpen, albumName, onClose, onConfirm, isProcessing }: DeleteAlbumDialogProps) {
  const [deleteFiles, setDeleteFiles] = useState(false);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[160] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
        
        <div className="p-6 sm:p-8 flex flex-col items-center text-center relative">
          <button 
            onClick={onClose}
            disabled={isProcessing}
            className="absolute top-4 right-4 p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100 transition-colors disabled:opacity-50"
          >
            <X size={20} />
          </button>

          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-6">
            <Trash2 size={32} className="text-red-600" />
          </div>
          
          <h3 className="text-2xl font-bold text-slate-900 mb-2">Delete Album?</h3>
          <p className="text-slate-500 mb-6">
            You are about to delete <strong>{albumName}</strong>. What would you like to do with the photos inside it?
          </p>

          {/* The Dangerous Checkbox */}
          <div className="w-full bg-slate-50 border border-slate-200 rounded-xl p-4 text-left mb-8 cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => setDeleteFiles(!deleteFiles)}>
            <label className="flex items-start gap-3 cursor-pointer">
              <input 
                type="checkbox" 
                className="mt-1 w-5 h-5 text-red-600 rounded border-slate-300 focus:ring-red-600"
                checked={deleteFiles}
                onChange={(e) => setDeleteFiles(e.target.checked)}
              />
              <div>
                <span className="block font-medium text-slate-900">Permanently delete files</span>
                <span className="block text-sm text-slate-500 mt-1">Also delete the physical photos and videos from my server's hard drive. This cannot be undone.</span>
              </div>
            </label>
          </div>
          
          <div className="flex w-full gap-3">
            <button
              onClick={onClose}
              disabled={isProcessing}
              className="flex-1 py-3 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium rounded-xl transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={() => onConfirm(deleteFiles)}
              disabled={isProcessing}
              className="flex-1 py-3 px-4 bg-red-600 hover:bg-red-700 text-white font-medium rounded-xl transition-colors shadow-md shadow-red-600/20 disabled:opacity-50 flex justify-center items-center"
            >
              {isProcessing ? 'Deleting...' : 'Delete Album'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}