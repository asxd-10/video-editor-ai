import { useState } from 'react';
import { FileText, Edit2, Save } from 'lucide-react';
import Button from '../common/Button';

export default function SummaryEditor({ summary, onSave, loading }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedSummary, setEditedSummary] = useState(summary || {
    video_summary: '',
    key_moments: [],
    content_type: 'presentation',
    main_topics: [],
    speaker_style: 'casual',
  });

  const handleSave = () => {
    onSave(editedSummary);
    setIsEditing(false);
  };

  if (!isEditing) {
    return (
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <FileText size={20} className="text-primary-600" />
            <h3 className="text-lg font-semibold text-dark-900">Video Summary</h3>
          </div>
          <Button
            variant="ghost"
            size="sm"
            icon={Edit2}
            onClick={() => setIsEditing(true)}
          >
            Edit
          </Button>
        </div>

        {editedSummary.video_summary ? (
          <div className="space-y-3">
            <div>
              <p className="text-sm text-dark-600 mb-1">Summary</p>
              <p className="text-dark-900">{editedSummary.video_summary}</p>
            </div>
            {editedSummary.main_topics && editedSummary.main_topics.length > 0 && (
              <div>
                <p className="text-sm text-dark-600 mb-1">Main Topics</p>
                <div className="flex flex-wrap gap-2">
                  {editedSummary.main_topics.map((topic, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-1 bg-primary-100 text-primary-700 rounded text-sm"
                    >
                      {topic}
                    </span>
                  ))}
                </div>
              </div>
            )}
            <div>
              <p className="text-sm text-dark-600 mb-1">Content Type</p>
              <p className="text-dark-900 capitalize">{editedSummary.content_type}</p>
            </div>
          </div>
        ) : (
          <p className="text-dark-600 text-sm">No summary provided. Click Edit to add one.</p>
        )}
      </div>
    );
  }

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <FileText size={20} className="text-primary-600" />
          <h3 className="text-lg font-semibold text-dark-900">Edit Summary</h3>
        </div>
        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsEditing(false)}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            icon={Save}
            onClick={handleSave}
            disabled={loading}
          >
            Save
          </Button>
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <label className="text-sm font-medium text-dark-700 mb-2 block">Video Summary</label>
          <textarea
            value={editedSummary.video_summary}
            onChange={(e) =>
              setEditedSummary({ ...editedSummary, video_summary: e.target.value })
            }
            placeholder="Brief overview of video content..."
            className="w-full px-4 py-3 rounded-lg border border-dark-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 outline-none resize-none"
            rows={4}
          />
        </div>

        <div>
          <label className="text-sm font-medium text-dark-700 mb-2 block">Content Type</label>
          <select
            value={editedSummary.content_type}
            onChange={(e) =>
              setEditedSummary({ ...editedSummary, content_type: e.target.value })
            }
            className="w-full px-4 py-2 rounded-lg border border-dark-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 outline-none"
          >
            <option value="tutorial">Tutorial</option>
            <option value="presentation">Presentation</option>
            <option value="interview">Interview</option>
            <option value="vlog">Vlog</option>
            <option value="educational">Educational</option>
          </select>
        </div>

        <div>
          <label className="text-sm font-medium text-dark-700 mb-2 block">Main Topics (comma-separated)</label>
          <input
            type="text"
            value={editedSummary.main_topics?.join(', ') || ''}
            onChange={(e) =>
              setEditedSummary({
                ...editedSummary,
                main_topics: e.target.value.split(',').map((t) => t.trim()).filter(Boolean),
              })
            }
            placeholder="video editing, tutorials, tips"
            className="w-full px-4 py-2 rounded-lg border border-dark-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 outline-none"
          />
        </div>
      </div>
    </div>
  );
}

