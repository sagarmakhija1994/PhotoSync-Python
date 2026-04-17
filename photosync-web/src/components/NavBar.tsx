import { Link, useLocation } from 'react-router-dom';
import { Image as ImageIcon, FolderHeart, Users } from 'lucide-react';

export default function NavBar() {
  const location = useLocation();
  const path = location.pathname;

  return (
    <nav className="flex space-x-1 border border-slate-200 bg-slate-100 p-1 rounded-xl">
      <Link 
        to="/" 
        className={`flex items-center gap-2 px-4 py-1.5 rounded-lg font-medium text-sm transition-all ${path === '/' ? 'bg-white shadow-sm text-blue-700' : 'text-slate-600 hover:text-slate-900'}`}
      >
        <ImageIcon size={16} /> Photos
      </Link>
      <Link 
        to="/albums" 
        className={`flex items-center gap-2 px-4 py-1.5 rounded-lg font-medium text-sm transition-all ${path.startsWith('/albums') ? 'bg-white shadow-sm text-blue-700' : 'text-slate-600 hover:text-slate-900'}`}
      >
        <FolderHeart size={16} /> Albums
      </Link>
      <Link 
        to="/network" 
        className={`flex items-center gap-2 px-4 py-1.5 rounded-lg font-medium text-sm transition-all ${path === '/network' ? 'bg-white shadow-sm text-blue-700' : 'text-slate-600 hover:text-slate-900'}`}
      >
        <Users size={16} /> Network
      </Link>
    </nav>
  );
}