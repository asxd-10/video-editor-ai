import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, Film, AlertCircle } from 'lucide-react';
import { validateVideoFile } from '../../utils/validators';
import clsx from 'clsx';

export default function UploadZone({ onFileSelect, maxSize = 500 * 1024 * 1024 }) {
  const [errors, setErrors] = useState([]);

  const onDrop = useCallback((acceptedFiles, rejectedFiles) => {
    setErrors([]);

    if (rejectedFiles.length > 0) {
      const newErrors = rejectedFiles.map(({ file, errors }) => 
        `${file.name}: ${errors.map(e => e.message).join(', ')}`
      );
      setErrors(newErrors);
      return;
    }

    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      const validation = validateVideoFile(file);

      if (!validation.valid) {
        setErrors(validation.errors);
        return;
      }

      onFileSelect(file);
    }
  }, [onFileSelect]);

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: {
      'video/*': ['.mp4', '.mov', '.avi', '.mkv', '.webm'],
    },
    maxSize,
    multiple: false,
  });

  return (
    <div className="w-full">
      <motion.div
        {...getRootProps()}
        className={clsx(
          'relative border-2 border-dashed rounded-3xl p-12 transition-all duration-300 cursor-pointer',
          'flex flex-col items-center justify-center min-h-[400px]',
          isDragActive && !isDragReject && 'border-primary-500 bg-primary-50',
          isDragReject && 'border-red-500 bg-red-50',
          !isDragActive && 'border-dark-300 hover:border-primary-400 hover:bg-dark-50'
        )}
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
      >
        <input {...getInputProps()} />

        <AnimatePresence mode="wait">
          {isDragActive ? (
            <motion.div
              key="dragging"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className="flex flex-col items-center"
            >
              <motion.div
                animate={{ 
                  y: [0, -10, 0],
                  rotate: [0, 5, -5, 0]
                }}
                transition={{ 
                  duration: 1,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
              >
                <Film size={80} className="text-primary-500" strokeWidth={1.5} />
              </motion.div>
              <p className="mt-6 text-xl font-medium text-primary-700">
                Drop your video here
              </p>
            </motion.div>
          ) : (
            <motion.div
              key="idle"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center text-center"
            >
              <div className="relative">
                <motion.div
                  animate={{ 
                    scale: [1, 1.1, 1],
                  }}
                  transition={{ 
                    duration: 2,
                    repeat: Infinity,
                    ease: "easeInOut"
                  }}
                  className="absolute inset-0 bg-primary-100 rounded-full opacity-50 blur-2xl"
                />
                <Upload size={80} className="relative text-primary-600" strokeWidth={1.5} />
              </div>
              
              <h3 className="mt-8 text-2xl font-semibold text-dark-900">
                Upload your video
              </h3>
              <p className="mt-3 text-lg text-dark-600 max-w-md">
                Drag and drop your video file here, or click to browse
              </p>
              
              <div className="mt-8 flex flex-wrap justify-center gap-2">
                {['.mp4', '.mov', '.avi', '.mkv', '.webm'].map((ext) => (
                  <span
                    key={ext}
                    className="px-3 py-1 bg-dark-100 text-dark-700 rounded-full text-sm font-medium"
                  >
                    {ext}
                  </span>
                ))}
              </div>
              
              <p className="mt-6 text-sm text-dark-500">
                Maximum file size: 500MB
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      <AnimatePresence>
        {errors.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-4"
          >
            {errors.map((error, index) => (
              <div
                key={index}
                className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-xl"
              >
                <AlertCircle size={20} className="text-red-600 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-800">{error}</p>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}