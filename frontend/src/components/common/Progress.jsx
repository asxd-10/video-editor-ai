import { motion } from 'framer-motion';
import clsx from 'clsx';

export default function Progress({ 
  value = 0, 
  max = 100, 
  size = 'md',
  variant = 'primary',
  showLabel = true,
  label,
  className 
}) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  const sizes = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3',
  };

  const variants = {
    primary: 'bg-primary-600',
    success: 'bg-green-500',
    warning: 'bg-yellow-500',
    danger: 'bg-red-500',
  };

  return (
    <div className={clsx('w-full', className)}>
      {showLabel && (
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-dark-700">
            {label || 'Progress'}
          </span>
          <span className="text-sm font-semibold text-dark-900">
            {Math.round(percentage)}%
          </span>
        </div>
      )}
      <div className={clsx('w-full bg-dark-200 rounded-full overflow-hidden', sizes[size])}>
        <motion.div
          className={clsx('h-full rounded-full', variants[variant])}
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
}