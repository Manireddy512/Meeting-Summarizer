import React, { useState } from 'react';
import axios from 'axios';

function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      // More reliable file type validation
      const fileName = selectedFile.name.toLowerCase();
      const allowedExtensions = ['.mp3', '.wav', '.m4a', '.flac'];
      const fileExtension = fileName.substring(fileName.lastIndexOf('.'));
      
      if (!allowedExtensions.includes(fileExtension)) {
        setError('Please select MP3, WAV, M4A, or FLAC files only');
        setFile(null);
        return;
      }
      
      // Validate file size (25MB)
      if (selectedFile.size > 25 * 1024 * 1024) {
        setError('File too large. Maximum size is 25MB');
        setFile(null);
        return;
      }
      
      setFile(selectedFile);
      setError('');
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select an audio file');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    const formData = new FormData();
    formData.append('audio', file);

    try {
      const response = await axios.post('/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 120000, // 2 minutes timeout
      });
      
      if (response.data.success) {
        setResult(response.data);
      } else {
        setError(response.data.error || 'Processing failed');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'An error occurred during processing');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-100 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-800 mb-4">
            🎯 Meeting Summarizer
          </h1>
          <p className="text-xl text-gray-600 mb-2">
            AI-powered meeting transcription and analysis
          </p>
          <p className="text-gray-500">
            Powered by Gemini Pro • Supports MP3, WAV, M4A, FLAC
          </p>
        </div>

        {/* Upload Section */}
        <div className="bg-white rounded-2xl shadow-xl p-8 mb-8">
          <div className="border-2 border-dashed border-gray-300 rounded-2xl p-12 text-center hover:border-blue-400 transition-colors">
            <div className="text-6xl mb-4">🎤</div>
            <input
              type="file"
              accept=".mp3,.wav,.m4a,.flac,audio/mp3,audio/wav,audio/m4a,audio/flac"
              onChange={handleFileChange}
              className="hidden"
              id="audio-upload"
            />
            <label
              htmlFor="audio-upload"
              className="cursor-pointer bg-blue-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors inline-block mb-4"
            >
              Choose Audio File
            </label>
            {file && (
              <div className="text-green-600 font-medium">
                ✅ Selected: {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
              </div>
            )}
            <p className="text-gray-500 text-sm mt-2">
              Maximum file size: 25MB • Supported: .mp3, .wav, .m4a, .flac
            </p>
          </div>

          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-600">❌ {error}</p>
            </div>
          )}

          <button
            onClick={handleUpload}
            disabled={loading || !file}
            className="w-full mt-6 bg-gradient-to-r from-green-500 to-blue-600 text-white py-4 rounded-lg font-semibold text-lg hover:from-green-600 hover:to-blue-700 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed transition-all transform hover:scale-105"
          >
            {loading ? (
              <div className="flex items-center justify-center">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white mr-3"></div>
                Processing with AI...
              </div>
            ) : (
              '🚀 Generate Summary'
            )}
          </button>
        </div>

        {/* Results Section */}
        {result && (
          <div className="space-y-8">
            {/* Metrics Card */}
            <div className="bg-white rounded-2xl shadow-xl p-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-4">📊 Meeting Metrics</h2>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-blue-50 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">{result.summary.meeting_metrics.total_decisions}</div>
                  <div className="text-gray-600">Key Decisions</div>
                </div>
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">{result.summary.meeting_metrics.total_action_items}</div>
                  <div className="text-gray-600">Action Items</div>
                </div>
                <div className="text-center p-4 bg-purple-50 rounded-lg">
                  <div className="text-2xl font-bold text-purple-600">{result.word_count} words</div>
                  <div className="text-gray-600">Transcript</div>
                </div>
                <div className="text-center p-4 bg-orange-50 rounded-lg">
                  <div className="text-2xl font-bold text-orange-600">{result.summary.meeting_metrics.key_topics.length}</div>
                  <div className="text-gray-600">Topics</div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Transcript */}
              <div className="bg-white rounded-2xl shadow-xl p-8">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-2xl font-bold text-gray-800">📝 Transcript</h2>
                  <span className="text-sm text-gray-500">{result.word_count} words</span>
                </div>
                <div className="bg-gray-50 rounded-lg p-6 max-h-96 overflow-y-auto">
                  <p className="text-gray-700 whitespace-pre-wrap leading-relaxed">
                    {result.transcript}
                  </p>
                </div>
              </div>

              {/* AI Analysis */}
              <div className="space-y-8">
                {/* Summary */}
                <div className="bg-white rounded-2xl shadow-xl p-8">
                  <h2 className="text-2xl font-bold text-gray-800 mb-4">📋 Executive Summary</h2>
                  <p className="text-gray-700 leading-relaxed">{result.summary.summary}</p>
                </div>

                {/* Key Decisions */}
                <div className="bg-white rounded-2xl shadow-xl p-8">
                  <h2 className="text-2xl font-bold text-gray-800 mb-4">🎯 Key Decisions</h2>
                  <ul className="space-y-3">
                    {result.summary.key_decisions.map((decision, index) => (
                      <li key={index} className="flex items-start">
                        <div className="w-2 h-2 bg-green-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                        <span className="text-gray-700">{decision}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Action Items */}
                <div className="bg-white rounded-2xl shadow-xl p-8">
                  <h2 className="text-2xl font-bold text-gray-800 mb-4">✅ Action Items</h2>
                  <div className="space-y-4">
                    {result.summary.action_items.map((item, index) => (
                      <div key={index} className="border-l-4 border-orange-500 pl-4 py-3 bg-orange-50 rounded-r-lg">
                        <p className="font-semibold text-gray-800">{item.task}</p>
                        <div className="flex flex-wrap items-center text-sm text-gray-600 mt-2 gap-4">
                          <span className="flex items-center">
                            <span className="font-medium">👤 Owner:</span> {item.owner}
                          </span>
                          <span className="flex items-center">
                            <span className="font-medium">📅 Deadline:</span> {item.deadline}
                          </span>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            item.priority === 'High' ? 'bg-red-100 text-red-800' :
                            item.priority === 'Medium' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-green-100 text-green-800'
                          }`}>
                            {item.priority} Priority
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Next Steps */}
                <div className="bg-white rounded-2xl shadow-xl p-8">
                  <h2 className="text-2xl font-bold text-gray-800 mb-4">🔜 Next Steps</h2>
                  <ul className="space-y-3">
                    {result.summary.next_steps.map((step, index) => (
                      <li key={index} className="flex items-start">
                        <div className="w-2 h-2 bg-blue-600 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                        <span className="text-gray-700">{step}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;