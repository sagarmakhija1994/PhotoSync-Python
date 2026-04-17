import { useState, useEffect } from 'react';
import { api } from '../api/apiClient';
import ConfirmDialog from './ConfirmDialog';
import { X, Search, UserPlus, ShieldCheck, UserMinus, Users, Link as LinkIcon } from 'lucide-react';

interface ShareAlbumModalProps {
  isOpen: boolean;
  albumId: number;
  albumName: string;
  onClose: () => void;
}

interface User {
  id: number;
  username: string;
}

export default function ShareAlbumModal({ isOpen, albumId, albumName, onClose }: ShareAlbumModalProps) {
  const [currentShares, setCurrentShares] = useState<User[]>([]);
  const [myConnections, setMyConnections] = useState<User[]>([]); // 💥 NEW: Store approved connections
  
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<User[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  const [revokeTarget, setRevokeTarget] = useState<User | null>(null);

  // 💥 NEW: Fetch both Shares and Connections when modal opens
  useEffect(() => {
    if (isOpen) {
      fetchModalData();
      setSearchQuery('');
      setSearchResults([]);
    }
  }, [isOpen, albumId]);

  const fetchModalData = async () => {
    try {
      const [sharesRes, connRes] = await Promise.all([
        api.get(`/albums/${albumId}/shares`),
        api.get('/network/connections')
      ]);
      
      setCurrentShares(sharesRes.data);
      
      // Map the network connection data (user_id) to match our User interface (id)
      const formattedConnections = connRes.data.map((c: any) => ({
        id: c.user_id,
        username: c.username
      }));
      setMyConnections(formattedConnections);
      
    } catch (err) {
      console.error("Failed to load modal data", err);
    }
  };

  // Keep the search engine for finding people OUTSIDE your network
  useEffect(() => {
    const searchUsers = async () => {
      if (searchQuery.length < 3) {
        setSearchResults([]);
        return;
      }
      setIsSearching(true);
      try {
        const response = await api.get(`/albums/available-users?q=${searchQuery}`);
        const existingIds = currentShares.map(s => s.id);
        const filtered = response.data.filter((u: User) => !existingIds.includes(u.id));
        setSearchResults(filtered);
      } catch (err) {
        console.error("Search failed", err);
      } finally {
        setIsSearching(false);
      }
    };

    const timeoutId = setTimeout(() => { searchUsers(); }, 300);
    return () => clearTimeout(timeoutId);
  }, [searchQuery, currentShares]);

  const handleShare = async (targetUsername: string) => {
    setIsProcessing(true);
    try {
      await api.post(`/albums/${albumId}/share`, { target_username: targetUsername });
      setSearchQuery('');
      
      // We only need to refresh the current shares, the connections list will auto-filter!
      const sharesRes = await api.get(`/albums/${albumId}/shares`);
      setCurrentShares(sharesRes.data);
    } catch (err) {
      alert("Failed to share album.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleUnshare = async () => {
    if (!revokeTarget) return;
    setIsProcessing(true);
    try {
      await api.delete(`/albums/${albumId}/share/${revokeTarget.id}`);
      
      const sharesRes = await api.get(`/albums/${albumId}/shares`);
      setCurrentShares(sharesRes.data);
      
      setRevokeTarget(null); 
    } catch (err) {
      alert("Failed to revoke access.");
    } finally {
      setIsProcessing(false);
    }
  };

  if (!isOpen) return null;

  // 💥 NEW: Filter out connections who already have access
  const availableConnections = myConnections.filter(
    conn => !currentShares.some(share => share.id === conn.id)
  );

  return (
    <div className="fixed inset-0 z-[150] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      
      <ConfirmDialog 
        isOpen={revokeTarget !== null}
        title="Revoke Access?"
        message={`Are you sure you want to remove ${revokeTarget?.username}'s access to this album? They will no longer be able to see or copy these photos.`}
        confirmText="Revoke Access"
        onConfirm={handleUnshare}
        onCancel={() => setRevokeTarget(null)}
        isProcessing={isProcessing}
      />

      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden flex flex-col h-[80vh] sm:h-[600px] relative">
        
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50 shrink-0">
          <div>
            <h2 className="text-xl font-bold text-slate-800">Share Album</h2>
            <p className="text-sm text-slate-500 truncate max-w-[250px]">{albumName}</p>
          </div>
          <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-200 transition-colors">
            <X size={20} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-8">
          
          {/* INVITE SECTION */}
          <section>
            <label className="text-sm font-bold text-slate-700 mb-2 block uppercase tracking-wider">Invite Family</label>
            <div className="relative mb-3">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search size={18} className="text-slate-400" />
              </div>
              <input
                type="text"
                className="w-full pl-10 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-600/20 focus:border-blue-600 transition-all text-slate-900"
                placeholder="Search by username..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              {isSearching && (
                <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                </div>
              )}
            </div>

            {/* LIVE SEARCH RESULTS */}
            {searchQuery.length >= 3 && (
              <div className="bg-white border border-slate-200 rounded-xl shadow-lg overflow-hidden animate-in fade-in zoom-in duration-200 mb-4">
                {searchResults.length === 0 && !isSearching ? (
                  <div className="p-4 text-center text-sm text-slate-500">No matching users found.</div>
                ) : (
                  searchResults.map(user => (
                    <div key={user.id} className="flex items-center justify-between p-3 hover:bg-slate-50 border-b border-slate-100 last:border-0">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold text-xs">
                          {user.username.charAt(0).toUpperCase()}
                        </div>
                        <span className="font-medium text-slate-700">{user.username}</span>
                      </div>
                      <button 
                        onClick={() => handleShare(user.username)}
                        disabled={isProcessing}
                        className="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 text-sm font-medium rounded-lg transition-colors flex items-center gap-1"
                      >
                        <UserPlus size={16} /> Share
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* 💥 NEW: QUICK SELECT FROM CONNECTIONS */}
            {searchQuery.length === 0 && (
              <div className="mt-4">
                <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <LinkIcon size={14} /> Quick Select Connections
                </p>
                {availableConnections.length === 0 ? (
                  <p className="text-sm text-slate-500 bg-slate-50 p-3 rounded-xl border border-slate-100">
                    No available connections to invite.
                  </p>
                ) : (
                  <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                    {availableConnections.map(user => (
                      <div key={user.id} className="flex items-center justify-between p-3 hover:bg-slate-50 border-b border-slate-100 last:border-0 transition-colors">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-bold text-xs">
                            {user.username.charAt(0).toUpperCase()}
                          </div>
                          <span className="font-medium text-slate-700">{user.username}</span>
                        </div>
                        <button 
                          onClick={() => handleShare(user.username)}
                          disabled={isProcessing}
                          className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-1 shadow-sm shadow-indigo-600/20 disabled:opacity-50"
                        >
                          <UserPlus size={16} /> Share
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </section>

          {/* CURRENT ACCESS SECTION */}
          <section>
            <label className="text-sm font-bold text-slate-700 mb-3 block uppercase tracking-wider flex items-center gap-2">
              <ShieldCheck size={16} className="text-emerald-500" /> Who Has Access
            </label>
            
            {currentShares.length === 0 ? (
              <div className="text-center p-6 bg-slate-50 border border-slate-200 border-dashed rounded-xl">
                <Users size={24} className="mx-auto text-slate-300 mb-2" />
                <p className="text-sm text-slate-500">Only you can see this album.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {currentShares.map(user => (
                  <div key={user.id} className="flex items-center justify-between p-3 bg-white border border-slate-200 rounded-xl shadow-sm group">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-700 font-bold text-xs">
                        {user.username.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <span className="block font-medium text-slate-700">{user.username}</span>
                        <span className="block text-[10px] text-emerald-600 font-bold uppercase tracking-tighter">Viewer</span>
                      </div>
                    </div>
                    <button 
                      onClick={() => setRevokeTarget(user)} 
                      disabled={isProcessing}
                      className="p-2 text-slate-300 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all opacity-0 group-hover:opacity-100"
                      title="Revoke Access"
                    >
                      <UserMinus size={18} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}