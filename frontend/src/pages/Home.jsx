import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Upload, Zap, Sparkles, Video } from 'lucide-react';
import Button from '../components/common/Button';
import React from 'react';

export default function Home() {
  const navigate = useNavigate();

  const features = [
    {
      icon: Upload,
      title: 'Easy Upload',
      description: 'Drag and drop your videos or browse to upload. Support for all major formats.',
    },
    {
      icon: Zap,
      title: 'Lightning Fast',
      description: 'Optimized processing pipeline ensures your videos are ready in seconds.',
    },
    {
      icon: Sparkles,
      title: 'Smart Processing',
      description: 'Automatic proxy generation, thumbnails, and metadata extraction.',
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-purple-50">
      {/* Hero Section */}
      <div className="max-w-7xl mx-auto px-6 py-20">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center"
        >
          {/* Logo/Icon */}
          <motion.div
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.2, duration: 0.5 }}
            className="inline-flex items-center justify-center w-20 h-20 bg-primary-600 rounded-3xl mb-8 shadow-apple-xl"
          >
            <Video size={40} className="text-white" strokeWidth={2} />
          </motion.div>

          {/* Headline */}
          <h1 className="text-hero font-display font-bold text-dark-900 mb-6">
            Your Video Platform
            <br />
            <span className="bg-gradient-to-r from-primary-600 to-purple-600 bg-clip-text text-transparent">
              Reimagined
            </span>
          </h1>

          <p className="text-xl text-dark-600 max-w-2xl mx-auto mb-12 leading-relaxed">
            Upload, process, and manage your videos with a beautiful, 
            fast, and intelligent platform built for creators.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button
              variant="primary"
              size="lg"
              icon={Upload}
              onClick={() => navigate('/upload')}
            >
              Upload Video
            </Button>
            <Button
              variant="secondary"
              size="lg"
              onClick={() => navigate('/library')}
            >
              View Library
            </Button>
          </div>

          {/* Stats */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="mt-16 grid grid-cols-3 gap-8 max-w-2xl mx-auto"
          >
            {[
              { label: 'Fast Processing', value: '<10s' },
              { label: 'Supported Formats', value: '5+' },
              { label: 'Max File Size', value: '500MB' },
            ].map((stat, index) => (
              <div key={index} className="text-center">
                <div className="text-3xl font-bold text-primary-600 mb-1">
                  {stat.value}
                </div>
                <div className="text-sm text-dark-600">{stat.label}</div>
              </div>
            ))}
          </motion.div>
        </motion.div>

        {/* Features */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.6 }}
          className="mt-32"
        >
          <h2 className="text-display font-bold text-center text-dark-900 mb-16">
            Everything you need
          </h2>

          <div className="grid md:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.7 + index * 0.1 }}
                whileHover={{ y: -8 }}
                className="card p-8 text-center"
              >
                <div className="w-16 h-16 bg-primary-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
                  <feature.icon size={32} className="text-primary-600" strokeWidth={2} />
                </div>
                <h3 className="text-xl font-semibold text-dark-900 mb-3">
                  {feature.title}
                </h3>
                <p className="text-dark-600 leading-relaxed">
                  {feature.description}
                </p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  );
}