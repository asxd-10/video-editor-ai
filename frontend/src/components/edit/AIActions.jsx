import { useState } from 'react';
import { motion } from 'framer-motion';
import { Mic, Sparkles, Loader2 } from 'lucide-react';
import Button from '../common/Button';
import Badge from '../common/Badge';

export default function AIActions({ videoId, onTranscribe, onAnalyze, onGenerateCandidates, transcriptStatus, analysisStatus }) {
  const [loading, setLoading] = useState({
    transcribe: false,
    analyze: false,
    candidates: false,
  });

  const handleTranscribe = async () => {
    setLoading({ ...loading, transcribe: true });
    try {
      await onTranscribe();
    } finally {
      setLoading({ ...loading, transcribe: false });
    }
  };

  const handleAnalyze = async () => {
    setLoading({ ...loading, analyze: true });
    try {
      await onAnalyze();
    } finally {
      setLoading({ ...loading, analyze: false });
    }
  };

  const handleGenerateCandidates = async () => {
    setLoading({ ...loading, candidates: true });
    try {
      await onGenerateCandidates();
    } finally {
      setLoading({ ...loading, candidates: false });
    }
  };

  return (
    <div className="card p-6">
      <h3 className="text-lg font-semibold text-dark-900 mb-4">AI Features</h3>
      <div className="space-y-3">
        {/* Transcription */}
        <div className="flex items-center justify-between p-3 rounded-lg border border-dark-200">
          <div className="flex items-center gap-3">
            <Mic size={20} className="text-primary-600" />
            <div>
              <p className="text-sm font-medium text-dark-900">Transcription</p>
              <p className="text-xs text-dark-500">
                {transcriptStatus === 'complete' ? 'Complete' : transcriptStatus === 'queued' ? 'Processing...' : 'Not started'}
              </p>
            </div>
          </div>
          {transcriptStatus === 'complete' ? (
            <Badge className="bg-green-100 text-green-700">Done</Badge>
          ) : (
            <Button
              variant="primary"
              size="sm"
              icon={loading.transcribe ? Loader2 : Mic}
              onClick={handleTranscribe}
              disabled={loading.transcribe || transcriptStatus === 'queued'}
            >
              {loading.transcribe ? 'Starting...' : 'Transcribe'}
            </Button>
          )}
        </div>

        {/* Analysis */}
        <div className="flex items-center justify-between p-3 rounded-lg border border-dark-200">
          <div className="flex items-center gap-3">
            <Sparkles size={20} className="text-primary-600" />
            <div>
              <p className="text-sm font-medium text-dark-900">Analysis</p>
              <p className="text-xs text-dark-500">
                {analysisStatus === 'complete' ? 'Complete' : analysisStatus === 'queued' ? 'Processing...' : 'Not started'}
              </p>
            </div>
          </div>
          {analysisStatus === 'complete' ? (
            <Badge className="bg-green-100 text-green-700">Done</Badge>
          ) : (
            <Button
              variant="primary"
              size="sm"
              icon={loading.analyze ? Loader2 : Sparkles}
              onClick={handleAnalyze}
              disabled={loading.analyze || analysisStatus === 'queued' || transcriptStatus !== 'complete'}
            >
              {loading.analyze ? 'Starting...' : 'Analyze'}
            </Button>
          )}
        </div>

        {/* Generate Candidates */}
        <div className="flex items-center justify-between p-3 rounded-lg border border-dark-200">
          <div className="flex items-center gap-3">
            <Sparkles size={20} className="text-primary-600" />
            <div>
              <p className="text-sm font-medium text-dark-900">Clip Candidates</p>
              <p className="text-xs text-dark-500">Generate best clips</p>
            </div>
          </div>
          <Button
            variant="primary"
            size="sm"
            icon={loading.candidates ? Loader2 : Sparkles}
            onClick={handleGenerateCandidates}
            disabled={loading.candidates || transcriptStatus !== 'complete'}
          >
            {loading.candidates ? 'Generating...' : 'Generate'}
          </Button>
        </div>
      </div>
    </div>
  );
}

