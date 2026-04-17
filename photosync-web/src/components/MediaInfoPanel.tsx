import { useState, useEffect } from 'react';
import { api } from '../api/apiClient';
import { Info, Camera, HardDrive, Calendar, Image as ImageIcon, X } from 'lucide-react';

interface MediaInfoPanelProps {
  photoId: number;
  isOpen: boolean;
  onClose: () => void;
}

export default function MediaInfoPanel({ photoId, isOpen, onClose }: MediaInfoPanelProps) {
  const [info, setInfo] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setIsLoading(true);
      api.get(`/photos/file/${photoId}/info`)
        .then(res => setInfo(res.data))
        .catch(err => console.error("Failed to load info", err))
        .finally(() => setIsLoading(false));
    }
  }, [photoId, isOpen]);

  if (!isOpen) return null;

  return (
    <div className="absolute top-0 right-0 bottom-0 w-80 bg-white shadow-2xl flex flex-col z-[200] animate-in slide-in-from-right-8 duration-300">
      <div className="flex items-center justify-between p-4 border-b border-slate-100">
        <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
          <Info size={20} className="text-blue-600" /> Details
        </h3>
        <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-full transition-colors">
          <X size={20} />
        </button>
      </div>

      <div className="p-6 flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex justify-center py-10"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div></div>
        ) : info ? (
          <div className="space-y-6">
            
            <div>
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">File</p>
              <p className="text-sm font-medium text-slate-800 break-all">{info.filename}</p>
              <div className="flex items-center gap-2 mt-2 text-sm text-slate-600">
                <HardDrive size={16} /> {(info.file_size / 1024 / 1024).toFixed(2)} MB
              </div>
            </div>

            <div className="h-px w-full bg-slate-100"></div>

            <div>
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Properties</p>
              <div className="space-y-3">
                <div className="flex items-center gap-3 text-sm text-slate-700">
                  <Calendar size={18} className="text-slate-400" />
                  {new Date(info.created_at.replace(':', '-').replace(':', '-')).toLocaleString()}
                </div>
                {info.media_type === 'photo' && (
                  <div className="flex items-center gap-3 text-sm text-slate-700">
                    <ImageIcon size={18} className="text-slate-400" />
                    {info.resolution}
                  </div>
                )}
              </div>
            </div>

            {info.media_type === 'photo' && info.camera_make !== "Unknown" && (
              <>
                <div className="h-px w-full bg-slate-100"></div>
                <div>
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Camera</p>
                  <div className="flex items-center gap-3 text-sm text-slate-700">
                    <Camera size={18} className="text-slate-400" />
                    <div>
                      <p className="font-medium">{info.camera_make}</p>
                      <p className="text-slate-500">{info.camera_model}</p>
                    </div>
                  </div>
                </div>
              </>
            )}

            <div className="h-px w-full bg-slate-100"></div>

            <div>
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Source Device</p>
              <p className="text-sm text-slate-700 bg-slate-50 px-3 py-2 rounded-lg border border-slate-100 inline-block">
                {info.device_name}
              </p>
            </div>

          </div>
        ) : (
          <p className="text-sm text-slate-500 text-center py-10">Details unavailable.</p>
        )}
      </div>
    </div>
  );
}