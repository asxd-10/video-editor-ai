import { motion } from 'framer-motion';
import { CheckCircle, XCircle, Loader, Film } from 'lucide-react';
import Progress from '../common/Progress';
import { formatFileSize } from '../../utils/formatters';
import clsx from 'clsx';

export default function UploadProgress({ upload }) {
  const { file, progress, status, error } = upload;

  const statusConfig = {
    uploading: {
      icon: Loader,
      iconClass: 'text-primary-600 animate-spin',
      label: 'Uploading',
      variant: 'primary',
    },
    processing: {
      icon: Loader,
      iconClass: 'text-purple-600 animate-spin',
      label: 'Processing',
      variant: 'primary',
    },
    completed: {
      icon: CheckCircle,
      iconClass: 'text-green-600',
      label: 'Completed',
      variant: 'success',
    },
    failed: {
      icon: XCircle,
      iconClass: 'text-red-600',
      label: 'Failed',
      variant: 'danger',
    },
  };

  const config = statusConfig[status] || statusConfig.uploading;
  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -100 }}
      className="card p-6"
    >
      <div className="flex items-start gap-4">
        {/* File Icon */}
        <div className="flex-shrink-0 w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center">
          <Film size={24} className="text-primary-600" />
        </div>

        {/* File Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <h4 className="text-base font-semibold text-dark-900 truncate">
                {file.name}
              </h4>
              <p className="text-sm text-dark-600 mt-1">
                {formatFileSize(file.size)}
              </p>
            </div>

            {/* Status Icon */}
            <div className="flex-shrink-0">
              <Icon size={24} className={config.iconClass} />
            </div>
          </div>

          {/* Progress Bar */}
          {status !== 'failed' && (
            <div className="mt-4">
              <Progress
                value={progress}
                variant={config.variant}
                size="md"
                label={config.label}
              />
            </div>
          )}

          {/* Error Message */}
          {error && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg"
            >
              <p className="text-sm text-red-800">{error}</p>
            </motion.div>
          )}
        </div>
      </div>
    </motion.div>
  );
}