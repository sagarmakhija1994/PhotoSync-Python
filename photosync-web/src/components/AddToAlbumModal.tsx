import { useState, useEffect } from 'react';
import { api } from '../api/apiClient';
import { X, FolderPlus } from 'lucide-react';

interface AddToAlbumModalProps {
  isOpen: boolean;
  onClose: () => void;
  photoIds: number[];
  onComplete: () => void;
}

export default function AddToAlbumModal({ isOpen, onClose, photoIds, onComplete }: AddToAlbumModalProps) {
  const [albums, setAlbums] = useState<{id: number, name: string}[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    if (isOpen) {
      api.get('/albums/').then(res => setAlbums(res.data.owned));
    }
  }, [isOpen]);

  const handleAdd = async (albumId: number) => {
    setIsProcessing(true);
    try {
      await api.post(`/albums/${albumId}/add-photos`, { photo_ids: photoIds });
      onComplete();
      onClose();
    } catch (err) {
      alert("Failed to add photos to album.");
    } finally {
      setIsProcessing(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[160] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
        <div className="px-6 py-4 border-b flex justify-between items-center bg-slate-50">
          <h2 className="text-xl font-bold text-slate-800">Add to Album</h2>
          <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600"><X size={20}/></button>
        </div>
        <div className="p-4 max-h-60 overflow-y-auto">
          {albums.length === 0 ? (
            <p className="text-center text-slate-500 py-4">No albums found. Create one first!</p>
          ) : (
            <div className="space-y-2">
              {albums.map(album => (
                <button
                  key={album.id}
                  onClick={() => handleAdd(album.id)}
                  disabled={isProcessing}
                  className="w-full flex items-center justify-between p-4 hover:bg-blue-50 border border-slate-100 rounded-xl transition-colors group"
                >
                  <span className="font-medium text-slate-700 group-hover:text-blue-700">{album.name}</span>
                  <FolderPlus size={18} className="text-slate-300 group-hover:text-blue-500" />
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}