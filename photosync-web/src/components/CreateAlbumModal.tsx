import React, { useState } from 'react';
import { api } from '../api/apiClient';
import { X, FolderPlus } from 'lucide-react';

interface CreateAlbumModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAlbumCreated: () => void;
}

export default function CreateAlbumModal({ isOpen, onClose, onAlbumCreated }: CreateAlbumModalProps) {
  const [albumName, setAlbumName] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!albumName.trim()) {
      setError('Album name cannot be empty.');
      return;
    }

    setIsProcessing(true);
    setError('');

    try {
      await api.post('/albums/create', { name: albumName.trim() });
      setAlbumName('');
      onAlbumCreated(); // Refresh the list
      onClose();        // Close the modal
    } catch (err: any) {
      console.error("Failed to create album", err);
      setError(err.response?.data?.detail || 'Failed to create album. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[150] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden transform transition-all">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
          <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
            <FolderPlus size={20} className="text-blue-600" />
            Create New Album
          </h2>
          <button 
            onClick={onClose} 
            disabled={isProcessing} 
            className="p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-200 transition-colors disabled:opacity-50"
          >
            <X size={20} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleCreate} className="p-6">
          {error && (
            <div className="mb-4 p-3 text-sm text-red-600 bg-red-50 rounded-lg border border-red-100">
              {error}
            </div>
          )}

          <div className="space-y-2 mb-6">
            <label className="text-sm font-semibold text-slate-700">Album Name</label>
            <input
              type="text"
              autoFocus
              className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-600/20 focus:border-blue-600 transition-all text-slate-900"
              placeholder="e.g., Summer Vacation 2026"
              value={albumName}
              onChange={(e) => setAlbumName(e.target.value)}
              disabled={isProcessing}
            />
          </div>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isProcessing}
              className="flex-1 py-2.5 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium rounded-xl transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isProcessing || !albumName.trim()}
              className="flex-1 py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-colors shadow-md shadow-blue-600/20 disabled:opacity-50 flex justify-center items-center"
            >
              {isProcessing ? 'Creating...' : 'Create Album'}
            </button>
          </div>
        </form>

      </div>
    </div>
  );
}