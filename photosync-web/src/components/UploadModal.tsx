import React, { useState, useRef } from 'react';
import { api } from '../api/apiClient';
import { X, UploadCloud, FileImage, CheckCircle, AlertCircle } from 'lucide-react';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadComplete: () => void;
}

interface FileWithStatus {
  file: File;
  status: 'pending' | 'hashing' | 'uploading' | 'success' | 'error';
  progress: number;
}

export default function UploadModal({ isOpen, onClose, onUploadComplete }: UploadModalProps) {
  const [files, setFiles] = useState<FileWithStatus[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const calculateHash = async (file: File): Promise<string> => {
    const buffer = await file.arrayBuffer();
    const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFiles = Array.from(e.dataTransfer.files).map(f => ({
      file: f, status: 'pending' as const, progress: 0
    }));
    setFiles(prev => [...prev, ...droppedFiles]);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files).map(f => ({
        file: f, status: 'pending' as const, progress: 0
      }));
      setFiles(prev => [...prev, ...selectedFiles]);
    }
  };

  const startUpload = async () => {
    setIsProcessing(true);

    for (let i = 0; i < files.length; i++) {
      if (files[i].status === 'success') continue;

      const currentFile = files[i].file;

      try {
        updateFileStatus(i, 'hashing', 0);
        const hash = await calculateHash(currentFile);
        const mediaType = currentFile.type.startsWith('video/') ? 'video' : 'photo';
        const relativePath = `Web Uploads/${currentFile.name}`;

        const formData = new FormData();
        formData.append('file', currentFile);
        formData.append('sha256', hash);
        formData.append('relative_path', relativePath);
        formData.append('media_type', mediaType);

        updateFileStatus(i, 'uploading', 10);

        await api.post('/photos/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 100));
            updateFileStatus(i, 'uploading', percentCompleted);
          }
        });

        updateFileStatus(i, 'success', 100);
      } catch (err) {
        console.error("Upload failed for", currentFile.name, err);
        updateFileStatus(i, 'error', 0);
      }
    }

    setIsProcessing(false);
    onUploadComplete();
  };

  const updateFileStatus = (index: number, status: FileWithStatus['status'], progress: number) => {
    setFiles(prev => {
      const newFiles = [...prev];
      newFiles[index] = { ...newFiles[index], status, progress };
      return newFiles;
    });
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 sm:p-6">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
          <h2 className="text-xl font-bold text-slate-800">Upload Media</h2>
          <button onClick={onClose} disabled={isProcessing} className="p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-200 disabled:opacity-50 transition-colors">
            <X size={24} />
          </button>
        </div>

        <div className="p-6">
          <div 
            className={`border-2 border-dashed rounded-xl p-8 text-center transition-all ${
              isDragging ? 'border-blue-500 bg-blue-50/50 scale-[1.02]' : 'border-slate-300 bg-slate-50 hover:border-blue-400 hover:bg-slate-100'
            }`}
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
          >
            <UploadCloud size={48} className={`mx-auto mb-4 ${isDragging ? 'text-blue-500' : 'text-slate-400'}`} />
            <h3 className="text-lg font-medium text-slate-700 mb-1">Drag and drop your photos here</h3>
            <p className="text-slate-500 text-sm mb-4">or click to browse your computer</p>
            
            <input 
              type="file" 
              multiple 
              className="hidden" 
              ref={fileInputRef} 
              onChange={handleFileSelect}
              accept="image/*,video/*,.heic,.dng,.arw"
            />
            
            <button 
              onClick={() => fileInputRef.current?.click()}
              disabled={isProcessing}
              className="px-6 py-2.5 bg-white border border-slate-300 text-slate-700 font-medium rounded-lg hover:bg-slate-50 shadow-sm transition-colors disabled:opacity-50"
            >
              Browse Files
            </button>
          </div>
        </div>

        {files.length > 0 && (
          <div className="flex-1 overflow-y-auto px-6 pb-6 space-y-3 min-h-[150px]">
            {files.map((fileObj, idx) => (
              <div key={idx} className="flex items-center gap-4 p-3 bg-white border border-slate-200 rounded-lg shadow-sm">
                <FileImage size={24} className="text-slate-400 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-700 truncate">{fileObj.file.name}</p>
                  <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2 overflow-hidden">
                    <div 
                      className={`h-1.5 rounded-full transition-all duration-300 ${fileObj.status === 'error' ? 'bg-red-500' : 'bg-blue-600'}`} 
                      style={{ width: `${fileObj.progress}%` }}
                    ></div>
                  </div>
                </div>
                <div className="shrink-0 w-24 text-right">
                  {fileObj.status === 'pending' && <button onClick={() => removeFile(idx)} className="text-xs text-red-500 font-medium hover:underline">Remove</button>}
                  {fileObj.status === 'hashing' && <span className="text-xs text-amber-500 font-medium animate-pulse">Hashing...</span>}
                  {fileObj.status === 'uploading' && <span className="text-xs text-blue-600 font-medium">{fileObj.progress}%</span>}
                  {fileObj.status === 'success' && <CheckCircle size={20} className="text-green-500 ml-auto" />}
                  {fileObj.status === 'error' && <AlertCircle size={20} className="text-red-500 ml-auto" />}
                </div>
              </div>
            ))}
          </div>
        )}

        {files.length > 0 && (
          <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-end gap-3">
            <button 
              onClick={() => setFiles([])} 
              disabled={isProcessing}
              className="px-4 py-2 text-slate-600 font-medium hover:bg-slate-200 rounded-lg transition-colors disabled:opacity-50"
            >
              Clear All
            </button>
            <button 
              onClick={startUpload}
              disabled={isProcessing || files.every(f => f.status === 'success')}
              className="px-6 py-2 bg-blue-600 text-white font-medium rounded-lg shadow-md hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {isProcessing ? 'Uploading...' : `Upload ${files.filter(f => f.status !== 'success').length} Files`}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}