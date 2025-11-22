import { motion } from 'framer-motion';
import { CheckCircle, Loader, XCircle } from 'lucide-react';
import clsx from 'clsx';

export default function ProcessingStatus({ logs }) {
  if (!logs || logs.length === 0) return null;

  const getStepIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle size={20} className="text-green-600" />;
      case 'failed':
        return <XCircle size={20} className="text-red-600" />;
      default:
        return <Loader size={20} className="text-primary-600 animate-spin" />;
    }
  };

  const getStepColor = (status) => {
    switch (status) {
      case 'completed':
        return 'border-green-500';
      case 'failed':
        return 'border-red-500';
      default:
        return 'border-primary-500';
    }
  };

  return (
    <div className="card p-6">
      <h3 className="text-lg font-semibold text-dark-900 mb-6">
        Processing Steps
      </h3>

      <div className="space-y-4">
        {logs.map((log, index) => (
          <motion.div
            key={log.step + index}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            className="flex items-start gap-4"
          >
            {/* Timeline */}
            <div className="relative flex flex-col items-center">
              <div className={clsx(
                'w-10 h-10 rounded-full border-2 flex items-center justify-center bg-white',
                getStepColor(log.status)
              )}>
                {getStepIcon(log.status)}
              </div>
              {index < logs.length - 1 && (
                <div className="w-0.5 h-8 bg-dark-200 my-2" />
              )}
            </div>

            {/* Content */}
            <div className="flex-1 pb-6">
              <div className="flex items-center justify-between mb-1">
                <h4 className="font-medium text-dark-900 capitalize">
                  {log.step.replace(/_/g, ' ')}
                </h4>
                <span className={clsx(
                  'text-xs font-semibold px-2 py-1 rounded-full',
                  log.status === 'completed' && 'bg-green-100 text-green-800',
                  log.status === 'failed' && 'bg-red-100 text-red-800',
                  log.status === 'started' && 'bg-primary-100 text-primary-800'
                )}>
                  {log.status}
                </span>
              </div>
              
              {log.message && (
                <p className="text-sm text-dark-600 mt-1">
                  {log.message}
                </p>
              )}
              
              {log.error && (
                <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-800">{log.error}</p>
                </div>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}