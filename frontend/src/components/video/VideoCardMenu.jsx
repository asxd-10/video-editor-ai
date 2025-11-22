import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MoreVertical, Play, Trash2, Eye } from 'lucide-react';

export default function VideoCardMenu({ video, onView, onDelete }) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  return (
    <div className="relative" ref={menuRef}>
      <motion.button
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-dark-100 transition-colors"
        onClick={(e) => {
          e.stopPropagation();
          setIsOpen(!isOpen);
        }}
      >
        <MoreVertical size={18} className="text-dark-600" />
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -10 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 mt-2 w-48 bg-white rounded-xl shadow-apple-lg border border-dark-200 py-2 z-50"
          >
            <button
              onClick={(e) => {
                e.stopPropagation();
                setIsOpen(false);
                onView(video);
              }}
              className="w-full px-4 py-2 text-left text-sm text-dark-700 hover:bg-dark-50 flex items-center gap-3 transition-colors"
            >
              <Eye size={16} />
              View Details
            </button>
            
            <button
              onClick={(e) => {
                e.stopPropagation();
                setIsOpen(false);
                onDelete(video);
              }}
              className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-3 transition-colors"
            >
              <Trash2 size={16} />
              Delete Video
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}