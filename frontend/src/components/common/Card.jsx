import { motion } from 'framer-motion';
import clsx from 'clsx';

export default function Card({ 
  children, 
  hover = true, 
  padding = true,
  className,
  ...props 
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={hover ? { y: -4, transition: { duration: 0.2 } } : {}}
      className={clsx(
        'card',
        padding && 'p-6',
        className
      )}
      {...props}
    >
      {children}
    </motion.div>
  );
}