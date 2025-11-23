import { useState, useRef, useEffect, forwardRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Play, 
  Pause, 
  Volume2, 
  VolumeX, 
  Maximize, 
  Minimize,
  SkipBack,
  SkipForward,
  Settings
} from 'lucide-react';
import { formatDuration } from '../../utils/formatters';
import clsx from 'clsx';

const VideoPlayer = forwardRef(function VideoPlayer({ src, poster, autoPlay = false, className }, ref) {
  const videoRef = useRef(null);
  
  // Expose video element via ref
  useEffect(() => {
    if (ref) {
      if (typeof ref === 'function') {
        ref(videoRef.current);
      } else {
        ref.current = videoRef.current;
      }
    }
  }, [ref]);
  const containerRef = useRef(null);
  const progressRef = useRef(null);
  
  const [playing, setPlaying] = useState(autoPlay);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [muted, setMuted] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [showControls, setShowControls] = useState(true);
  const [buffered, setBuffered] = useState(0);
  const [loading, setLoading] = useState(true);

  // Mouse idle detection
  const hideControlsTimeout = useRef(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleLoadedMetadata = () => {
      setDuration(video.duration);
      setLoading(false);
    };

    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime);
    };

    const handleProgress = () => {
      if (video.buffered.length > 0) {
        const bufferedEnd = video.buffered.end(video.buffered.length - 1);
        const bufferedPercent = (bufferedEnd / video.duration) * 100;
        setBuffered(bufferedPercent);
      }
    };

    const handleEnded = () => {
      setPlaying(false);
    };

    const handleWaiting = () => setLoading(true);
    const handleCanPlay = () => setLoading(false);

    video.addEventListener('loadedmetadata', handleLoadedMetadata);
    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('progress', handleProgress);
    video.addEventListener('ended', handleEnded);
    video.addEventListener('waiting', handleWaiting);
    video.addEventListener('canplay', handleCanPlay);

    return () => {
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('progress', handleProgress);
      video.removeEventListener('ended', handleEnded);
      video.removeEventListener('waiting', handleWaiting);
      video.removeEventListener('canplay', handleCanPlay);
    };
  }, []);

  // Auto-hide controls
  const handleMouseMove = () => {
    setShowControls(true);
    if (hideControlsTimeout.current) {
      clearTimeout(hideControlsTimeout.current);
    }
    if (playing) {
      hideControlsTimeout.current = setTimeout(() => {
        setShowControls(false);
      }, 3000);
    }
  };

  const togglePlay = () => {
    if (playing) {
      videoRef.current?.pause();
    } else {
      videoRef.current?.play();
    }
    setPlaying(!playing);
  };

  const handleProgressClick = (e) => {
    if (!progressRef.current || !videoRef.current || !duration) return;
    
    const bounds = progressRef.current.getBoundingClientRect();
    const x = e.clientX - bounds.left;
    const percentage = Math.max(0, Math.min(1, x / bounds.width));
    const newTime = percentage * duration;
    
    if (videoRef.current) {
      videoRef.current.currentTime = newTime;
      setCurrentTime(newTime);
    }
  };

  const handleVolumeChange = (e) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    videoRef.current.volume = newVolume;
    setMuted(newVolume === 0);
  };

  const toggleMute = () => {
    if (muted) {
      videoRef.current.volume = volume;
      setMuted(false);
    } else {
      videoRef.current.volume = 0;
      setMuted(true);
    }
  };

  const toggleFullscreen = () => {
    if (!fullscreen) {
      if (containerRef.current.requestFullscreen) {
        containerRef.current.requestFullscreen();
      }
      setFullscreen(true);
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
      setFullscreen(false);
    }
  };

  const skip = (seconds) => {
    const newTime = Math.max(0, Math.min(duration, currentTime + seconds));
    videoRef.current.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div
      ref={containerRef}
      className={clsx('relative bg-black rounded-2xl overflow-hidden group', className)}
      onMouseMove={handleMouseMove}
      onMouseLeave={() => playing && setShowControls(false)}
    >
      {/* Video Element */}
      <video
        ref={videoRef}
        src={src}
        poster={poster}
        className="w-full h-full"
        onClick={togglePlay}
        playsInline
      />

      {/* Loading Spinner */}
      <AnimatePresence>
        {loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 flex items-center justify-center bg-black/30 backdrop-blur-sm"
          >
            <div className="w-16 h-16 border-4 border-white/30 border-t-white rounded-full animate-spin" />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Center Play Button */}
      <AnimatePresence>
        {!playing && !loading && (
          <motion.button
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.8, opacity: 0 }}
            onClick={togglePlay}
            className="absolute inset-0 flex items-center justify-center bg-black/20 backdrop-blur-sm"
          >
            <motion.div
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              className="w-20 h-20 bg-white rounded-full flex items-center justify-center shadow-apple-xl"
            >
              <Play size={40} className="text-dark-900 ml-1" fill="currentColor" />
            </motion.div>
          </motion.button>
        )}
      </AnimatePresence>

      {/* Controls */}
      <AnimatePresence>
        {showControls && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 via-black/60 to-transparent p-6"
          >
            {/* Progress Bar */}
            <div className="mb-4">
              <div
                ref={progressRef}
                className="relative h-1.5 bg-white/30 rounded-full cursor-pointer group/progress"
                onClick={handleProgressClick}
              >
                {/* Buffered */}
                <div
                  className="absolute h-full bg-white/20 rounded-full transition-all"
                  style={{ width: `${buffered}%` }}
                />
                
                {/* Progress */}
                <motion.div
                  className="absolute h-full bg-white rounded-full"
                  style={{ width: `${progress}%` }}
                />
                
                {/* Scrubber */}
                <motion.div
                  className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-white rounded-full shadow-lg opacity-0 group-hover/progress:opacity-100 transition-opacity"
                  style={{ left: `${progress}%`, marginLeft: '-8px' }}
                  whileHover={{ scale: 1.2 }}
                />
              </div>

              {/* Time Display */}
              <div className="flex justify-between items-center mt-2 text-sm text-white/90">
                <span>{formatDuration(currentTime)}</span>
                <span>{formatDuration(duration)}</span>
              </div>
            </div>

            {/* Control Buttons */}
            <div className="flex items-center justify-between">
              {/* Left Controls */}
              <div className="flex items-center gap-3">
                {/* Play/Pause */}
                <motion.button
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.9 }}
                  onClick={togglePlay}
                  className="w-10 h-10 flex items-center justify-center rounded-full bg-white/20 hover:bg-white/30 transition-colors"
                >
                  {playing ? (
                    <Pause size={20} className="text-white" fill="currentColor" />
                  ) : (
                    <Play size={20} className="text-white ml-0.5" fill="currentColor" />
                  )}
                </motion.button>

                {/* Skip Backward */}
                <motion.button
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.9 }}
                  onClick={() => skip(-10)}
                  className="w-9 h-9 flex items-center justify-center rounded-full hover:bg-white/20 transition-colors"
                >
                  <SkipBack size={18} className="text-white" />
                </motion.button>

                {/* Skip Forward */}
                <motion.button
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.9 }}
                  onClick={() => skip(10)}
                  className="w-9 h-9 flex items-center justify-center rounded-full hover:bg-white/20 transition-colors"
                >
                  <SkipForward size={18} className="text-white" />
                </motion.button>

                {/* Volume */}
                <div className="flex items-center gap-2 group/volume">
                  <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={toggleMute}
                    className="w-9 h-9 flex items-center justify-center rounded-full hover:bg-white/20 transition-colors"
                  >
                    {muted || volume === 0 ? (
                      <VolumeX size={18} className="text-white" />
                    ) : (
                      <Volume2 size={18} className="text-white" />
                    )}
                  </motion.button>
                  
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={muted ? 0 : volume}
                    onChange={handleVolumeChange}
                    className="w-0 group-hover/volume:w-20 transition-all duration-300 opacity-0 group-hover/volume:opacity-100"
                    style={{
                      background: `linear-gradient(to right, white 0%, white ${(muted ? 0 : volume) * 100}%, rgba(255,255,255,0.3) ${(muted ? 0 : volume) * 100}%, rgba(255,255,255,0.3) 100%)`
                    }}
                  />
                </div>
              </div>

              {/* Right Controls */}
              <div className="flex items-center gap-3">
                {/* Settings - Placeholder for future settings menu */}
                <motion.button
                  whileHover={{ scale: 1.1, rotate: 90 }}
                  whileTap={{ scale: 0.9 }}
                  className="w-9 h-9 flex items-center justify-center rounded-full hover:bg-white/20 transition-colors"
                  title="Settings (Coming soon)"
                  disabled
                >
                  <Settings size={18} className="text-white/60" />
                </motion.button>

                {/* Fullscreen */}
                <motion.button
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.9 }}
                  onClick={toggleFullscreen}
                  className="w-9 h-9 flex items-center justify-center rounded-full hover:bg-white/20 transition-colors"
                >
                  {fullscreen ? (
                    <Minimize size={18} className="text-white" />
                  ) : (
                    <Maximize size={18} className="text-white" />
                  )}
                </motion.button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
});

export default VideoPlayer;