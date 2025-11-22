import React, { useState, useCallback, useRef } from 'react';
import { Upload, Download, Play, Settings, FileText, AlertTriangle, CheckCircle, XCircle, Eye, Code, Monitor, ArrowLeft, Undo, AlertCircle, Zap, RefreshCw, Shield } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

function App() {
  const [files, setFiles] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [analysisResults, setAnalysisResults] = useState({});
  const [loading, setLoading] = useState(false);
  const [selectedModels, setSelectedModels] = useState(['gpt-4o']);
  const [selectedIssue, setSelectedIssue] = useState(null);
  const [showIssueModal, setShowIssueModal] = useState(false);
  const [issueModalTab, setIssueModalTab] = useState('code');
  const [remediationResults, setRemediationResults] = useState({});
  const [currentPage, setCurrentPage] = useState('configuration'); // 'configuration' or 'results'

  // Enhanced remediation states
  const [remediationPreviews, setRemediationPreviews] = useState({});
  const [showRemediationModal, setShowRemediationModal] = useState(false);
  const [currentRemediation, setCurrentRemediation] = useState(null);
  const [remediationTab, setRemediationTab] = useState('preview'); // 'preview', 'diff', 'validation'
  const [appliedRemediations, setAppliedRemediations] = useState({});

  const fileInputRef = useRef(null);

  const availableModels = [
    { id: 'gpt-4o', name: 'GPT-4o', description: 'Advanced reasoning and code understanding' },
    { id: 'claude-opus-4', name: 'Claude Opus 4', description: 'Strong analytical capabilities' },
    { id: 'deepseek-v3', name: 'DeepSeek-V3', description: 'Code-focused analysis' },
    { id: 'llama-maverick', name: 'LLaMA Maverick', description: 'Alternative perspective validation' }
  ];

  const handleFileUpload = useCallback(async (event) => {
    const uploadedFiles = Array.from(event.target.files);
    if (uploadedFiles.length === 0) return;

    setLoading(true);
    try {
      const formData = new FormData();
      uploadedFiles.forEach(file => {
        formData.append('files', file);
      });

      const response = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Upload failed');

      const result = await response.json();
      setSessionId(result.session_id);
      setFiles(result.files);
    } catch (error) {
      alert(`Upload failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleAnalysis = useCallback(async () => {
    if (!sessionId || selectedModels.length === 0) return;

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          models: selectedModels,
          analysis_type: 'detection'
        }),
      });

      if (!response.ok) throw new Error('Analysis failed');

      const result = await response.json();
      setAnalysisResults(result.results);
      setCurrentPage('results');
    } catch (error) {
      alert(`Analysis failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }, [sessionId, selectedModels]);

  // Enhanced remediation functions
  const handleRemediationPreview = useCallback(async (issueId, model, issue) => {
    if (!sessionId) return;

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/remediate/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          issue_id: issueId,
          model: model
        }),
      });

      if (!response.ok) throw new Error('Preview generation failed');

      const result = await response.json();

      setRemediationPreviews(prev => ({
        ...prev,
        [issueId]: { ...result, model, issue }
      }));

      setCurrentRemediation({ issueId, model, issue, preview: result });
      setShowRemediationModal(true);
      setRemediationTab('preview');

    } catch (error) {
      alert(`Preview generation failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const handleRemediationApply = useCallback(async (issueId, model, forceApply = false) => {
    if (!sessionId) return;

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/remediate/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          issue_id: issueId,
          model: model,
          force_apply: forceApply
        }),
      });

      const result = await response.json();

      if (response.status === 422) {
        // Quality score too low - show options
        const userConfirm = window.confirm(
          `Remediation quality score (${result.quality_score?.toFixed(2)}) is below threshold. Apply anyway?`
        );

        if (userConfirm) {
          return handleRemediationApply(issueId, model, true);
        }
        return;
      }

      if (!response.ok) throw new Error(result.detail || 'Remediation failed');

      setAppliedRemediations(prev => ({
        ...prev,
        [issueId]: result
      }));

      setShowRemediationModal(false);
      alert('Remediation applied successfully!');

    } catch (error) {
      alert(`Remediation failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const handleRemediationRollback = useCallback(async (issueId) => {
    if (!sessionId) return;

    const userConfirm = window.confirm('Are you sure you want to rollback this remediation?');
    if (!userConfirm) return;

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/remediate/rollback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          issue_id: issueId
        }),
      });

      if (!response.ok) throw new Error('Rollback failed');

      const result = await response.json();

      setAppliedRemediations(prev => {
        const newState = { ...prev };
        delete newState[issueId];
        return newState;
      });

      alert('Remediation rolled back successfully!');

    } catch (error) {
      alert(`Rollback failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const downloadFixedCode = useCallback(async () => {
    if (!sessionId) return;

    try {
      const response = await fetch(`${API_BASE}/download/${sessionId}/fixed-code`);
      if (!response.ok) throw new Error('Download failed');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `fixed_code_${sessionId}.zip`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      alert(`Download failed: ${error.message}`);
    }
  }, [sessionId]);

  const downloadReport = useCallback(async () => {
    if (!sessionId) return;

    try {
      const response = await fetch(`${API_BASE}/download/${sessionId}/report`);
      if (!response.ok) throw new Error('Report generation failed');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `accessibility_report_${sessionId}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      alert(`Report generation failed: ${error.message}`);
    }
  }, [sessionId]);

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'A': return 'bg-red-100 text-red-800 border-red-200';
      case 'AA': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'AAA': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getCategoryColor = (category) => {
    switch (category) {
      case 'perceivable': return 'bg-blue-100 text-blue-800';
      case 'operable': return 'bg-green-100 text-green-800';
      case 'understandable': return 'bg-purple-100 text-purple-800';
      case 'robust': return 'bg-indigo-100 text-indigo-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getQualityScoreColor = (score) => {
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const openIssueModal = (issue, model, fileName) => {
    setSelectedIssue({ ...issue, model, fileName });
    setShowIssueModal(true);
    setIssueModalTab('code');
  };

  const getAllIssues = () => {
    const allIssues = [];
    Object.entries(analysisResults).forEach(([model, modelResults]) => {
      if (Array.isArray(modelResults)) {
        modelResults.forEach(fileResult => {
          if (fileResult.issues) {
            fileResult.issues.forEach(issue => {
              allIssues.push({
                ...issue,
                model,
                fileName: fileResult.file_info?.name || 'Unknown',
                filePath: fileResult.file_info?.path || ''
              });
            });
          }
        });
      }
    });
    return allIssues;
  };

  const goBackToConfiguration = () => {
    setCurrentPage('configuration');
  };

  // Enhanced Remediation Modal Component
  const renderRemediationModal = () => {
    if (!showRemediationModal || !currentRemediation) return null;

    const { issueId, model, issue, preview } = currentRemediation;

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg w-11/12 h-5/6 flex flex-col max-w-6xl">
          {/* Modal Header */}
          <div className="flex justify-between items-center p-6 border-b bg-gradient-to-r from-blue-50 to-indigo-50">
            <div className="flex items-center gap-4">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Zap className="text-blue-600" size={24} />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">Enhanced Remediation</h2>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-sm text-gray-600">{issue.wcag_guideline}</span>
                  <span className={`px-2 py-1 rounded text-xs border ${getSeverityColor(issue.severity)}`}>
                    Level {issue.severity}
                  </span>
                  <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                    {model}
                  </span>
                </div>
              </div>
            </div>
            <button
              onClick={() => setShowRemediationModal(false)}
              className="text-gray-500 hover:text-gray-700 p-2"
            >
              <XCircle size={24} />
            </button>
          </div>

          {/* Tab Navigation */}
          <div className="flex border-b bg-gray-50">
            <button
              className={`px-6 py-3 font-medium transition-colors ${
                remediationTab === 'preview' 
                  ? 'border-b-2 border-blue-500 text-blue-600 bg-white' 
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              onClick={() => setRemediationTab('preview')}
            >
              <Eye className="inline mr-2" size={16} />
              Fix Preview
            </button>
            <button
              className={`px-6 py-3 font-medium transition-colors ${
                remediationTab === 'diff' 
                  ? 'border-b-2 border-blue-500 text-blue-600 bg-white' 
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              onClick={() => setRemediationTab('diff')}
            >
              <Code className="inline mr-2" size={16} />
              Code Changes
            </button>
            <button
              className={`px-6 py-3 font-medium transition-colors ${
                remediationTab === 'validation' 
                  ? 'border-b-2 border-blue-500 text-blue-600 bg-white' 
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              onClick={() => setRemediationTab('validation')}
            >
              <Shield className="inline mr-2" size={16} />
              Validation
            </button>
          </div>

          {/* Tab Content */}
          <div className="flex-1 p-6 overflow-auto">
            {remediationTab === 'preview' && (
              <div className="space-y-6">
                {/* Quality Score */}
                <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-4 rounded-lg border">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-semibold text-gray-900">Remediation Quality</h3>
                    <div className={`text-2xl font-bold ${getQualityScoreColor(preview.quality_score || 0)}`}>
                      {((preview.quality_score || 0) * 100).toFixed(0)}%
                    </div>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all duration-300 ${
                        (preview.quality_score || 0) >= 0.8 ? 'bg-green-500' :
                        (preview.quality_score || 0) >= 0.6 ? 'bg-yellow-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${((preview.quality_score || 0) * 100)}%` }}
                    ></div>
                  </div>
                </div>

                {/* Changes Summary */}
                <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                  <h3 className="font-semibold text-green-800 mb-2">Proposed Changes</h3>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-green-700 font-medium">Changes: </span>
                      <span className="text-green-800">{preview.changes?.length || 0}</span>
                    </div>
                    <div>
                      <span className="text-green-700 font-medium">Validation: </span>
                      <span className="text-green-800">
                        {preview.validation?.wcag_compliance ? '✓ WCAG Compliant' : '⚠ Needs Review'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Estimated Impact */}
                {preview.estimated_impact && (
                  <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                    <h3 className="font-semibold text-blue-800 mb-2">Expected Impact</h3>
                    <p className="text-blue-700">{preview.estimated_impact}</p>
                  </div>
                )}

                {/* Individual Changes */}
                <div className="space-y-4">
                  <h3 className="font-semibold text-gray-900">Individual Changes</h3>
                  {preview.changes?.map((change, index) => (
                    <div key={index} className="border rounded-lg p-4 bg-gray-50">
                      <div className="flex items-start justify-between mb-2">
                        <span className="text-sm font-medium text-gray-600">
                          Line {change.line_number}
                        </span>
                        <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                          {change.wcag_principle || 'Accessibility'}
                        </span>
                      </div>

                      <div className="space-y-2">
                        <div>
                          <p className="text-xs text-gray-500 mb-1">Before:</p>
                          <pre className="text-sm bg-red-50 p-2 rounded border text-red-800 overflow-x-auto">
                            <code>{change.original}</code>
                          </pre>
                        </div>

                        <div>
                          <p className="text-xs text-gray-500 mb-1">After:</p>
                          <pre className="text-sm bg-green-50 p-2 rounded border text-green-800 overflow-x-auto">
                            <code>{change.fixed}</code>
                          </pre>
                        </div>

                        <div className="bg-blue-50 p-2 rounded">
                          <p className="text-xs text-blue-600 font-medium mb-1">Explanation:</p>
                          <p className="text-sm text-blue-800">{change.explanation}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {remediationTab === 'diff' && (
              <div className="space-y-4">
                <h3 className="font-semibold text-gray-900">Code Diff</h3>

                {preview.diff?.unified_diff ? (
                  <div className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto">
                    <pre className="text-sm">
                      <code>{preview.diff.unified_diff}</code>
                    </pre>
                  </div>
                ) : (
                  <div className="bg-gray-50 p-4 rounded-lg border">
                    <p className="text-gray-600">Diff view not available</p>
                  </div>
                )}

                {preview.diff?.statistics && (
                  <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                    <h4 className="font-medium text-blue-800 mb-2">Change Statistics</h4>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-green-600 font-medium">Added: </span>
                        <span>{preview.diff.statistics.lines_added}</span>
                      </div>
                      <div>
                        <span className="text-red-600 font-medium">Removed: </span>
                        <span>{preview.diff.statistics.lines_deleted}</span>
                      </div>
                      <div>
                        <span className="text-blue-600 font-medium">Modified: </span>
                        <span>{preview.diff.statistics.lines_modified}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {remediationTab === 'validation' && (
              <div className="space-y-6">
                <h3 className="font-semibold text-gray-900">Validation Results</h3>

                {/* WCAG Compliance */}
                <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                  <h4 className="font-medium text-green-800 mb-2">WCAG 2.2 Compliance</h4>
                  <p className="text-green-700">
                    {preview.validation?.wcag_compliance || 'Validation completed successfully'}
                  </p>
                </div>

                {/* Testing Instructions */}
                {preview.validation?.testing_instructions && (
                  <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                    <h4 className="font-medium text-blue-800 mb-2">Testing Instructions</h4>
                    <p className="text-blue-700">{preview.validation.testing_instructions}</p>
                  </div>
                )}

                {/* Infotainment Considerations */}
                {preview.validation?.infotainment_considerations && (
                  <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
                    <h4 className="font-medium text-purple-800 mb-2">Automotive Considerations</h4>
                    <p className="text-purple-700">{preview.validation.infotainment_considerations}</p>
                  </div>
                )}

                {/* Potential Side Effects */}
                {preview.validation?.potential_side_effects && (
                  <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
                    <h4 className="font-medium text-yellow-800 mb-2">Potential Side Effects</h4>
                    <p className="text-yellow-700">{preview.validation.potential_side_effects}</p>
                  </div>
                )}

                {/* Accessibility Recheck */}
                {preview.accessibility_recheck && (
                  <div className="bg-indigo-50 p-4 rounded-lg border border-indigo-200">
                    <h4 className="font-medium text-indigo-800 mb-2">Post-Fix Analysis</h4>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-indigo-700 font-medium">Issues Remaining: </span>
                        <span className={preview.accessibility_recheck.similar_issues_remaining === 0 ? 'text-green-600' : 'text-red-600'}>
                          {preview.accessibility_recheck.similar_issues_remaining || 0}
                        </span>
                      </div>
                      <div>
                        <span className="text-indigo-700 font-medium">Likely Fixed: </span>
                        <span className={preview.accessibility_recheck.likely_fixed ? 'text-green-600' : 'text-red-600'}>
                          {preview.accessibility_recheck.likely_fixed ? 'Yes' : 'No'}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Modal Footer */}
          <div className="flex justify-between items-center p-6 border-t bg-gray-50">
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${
                (preview.quality_score || 0) >= 0.8 ? 'bg-green-500' :
                (preview.quality_score || 0) >= 0.6 ? 'bg-yellow-500' : 'bg-red-500'
              }`}></div>
              <span className="text-sm text-gray-600">
                Quality Score: {((preview.quality_score || 0) * 100).toFixed(0)}%
              </span>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setShowRemediationModal(false)}
                className="px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>

              <button
                onClick={() => handleRemediationApply(issueId, model)}
                className={`px-6 py-2 rounded-lg text-white font-medium transition-colors ${
                  (preview.quality_score || 0) >= 0.7 
                    ? 'bg-green-600 hover:bg-green-700' 
                    : 'bg-yellow-600 hover:bg-yellow-700'
                }`}
              >
                <CheckCircle className="inline mr-2" size={16} />
                {(preview.quality_score || 0) >= 0.7 ? 'Apply Fix' : 'Apply Anyway'}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderIssueModal = () => {
    if (!showIssueModal || !selectedIssue) return null;

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg w-11/12 h-5/6 flex flex-col">
          {/* Modal Header */}
          <div className="flex justify-between items-center p-4 border-b">
            <div>
              <h2 className="text-xl font-bold">{selectedIssue.wcag_guideline}</h2>
              <p className="text-gray-600">{selectedIssue.fileName}</p>
            </div>
            <button
              onClick={() => setShowIssueModal(false)}
              className="text-gray-500 hover:text-gray-700"
            >
              <XCircle size={24} />
            </button>
          </div>

          {/* Tab Navigation */}
          <div className="flex border-b">
            <button
              className={`px-4 py-2 font-medium ${issueModalTab === 'code' ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-500'}`}
              onClick={() => setIssueModalTab('code')}
            >
              <Code className="inline mr-2" size={16} />
              Code View
            </button>
            <button
              className={`px-4 py-2 font-medium ${issueModalTab === 'preview' ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-500'}`}
              onClick={() => setIssueModalTab('preview')}
            >
              <Monitor className="inline mr-2" size={16} />
              UI Preview
            </button>
          </div>

          {/* Tab Content */}
          <div className="flex-1 p-4 overflow-auto">
            {issueModalTab === 'code' && (
              <div className="space-y-4">
                <div className="bg-gray-100 p-4 rounded">
                  <h3 className="font-semibold mb-2">Issue Description</h3>
                  <p>{selectedIssue.description}</p>
                </div>

                <div className="bg-red-50 p-4 rounded border">
                  <h3 className="font-semibold mb-2">Problematic Code (Lines {selectedIssue.line_numbers?.join(', ')})</h3>
                  <pre className="bg-white p-3 rounded border overflow-x-auto text-sm">
                    <code>{selectedIssue.code_snippet}</code>
                  </pre>
                </div>

                <div className="bg-green-50 p-4 rounded border">
                  <h3 className="font-semibold mb-2">Recommendation</h3>
                  <p>{selectedIssue.recommendation}</p>
                </div>

                {selectedIssue.code_context && (
                  <div className="bg-blue-50 p-4 rounded border">
                    <h3 className="font-semibold mb-2">Code Context</h3>
                    <div className="bg-white p-3 rounded border overflow-x-auto">
                      {selectedIssue.code_context.lines?.map((line, idx) => (
                        <div
                          key={idx}
                          className={`flex ${line.highlighted ? 'bg-red-100' : ''}`}
                        >
                          <span className="w-12 text-gray-500 text-sm mr-4">{line.number}</span>
                          <pre className="flex-1 text-sm"><code>{line.content}</code></pre>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {issueModalTab === 'preview' && (
              <div className="space-y-4">
                <div className="bg-gray-100 p-4 rounded">
                  <h3 className="font-semibold mb-2">Infotainment UI Preview</h3>
                  <p className="text-sm text-gray-600 mb-4">
                    Simulated interface showing the problematic element
                  </p>

                  {/* Simulated UI Preview */}
                  <div className="bg-black rounded-lg p-6 text-white relative" style={{minHeight: '300px'}}>
                    {/* Simulated infotainment interface */}
                    <div className="flex justify-between items-center mb-4">
                      <div className="text-sm">12:34 PM</div>
                      <div className="text-sm">Connected to Vehicle</div>
                    </div>

                    <div className="grid grid-cols-3 gap-4 mb-6">
                      <div className="bg-gray-800 p-4 rounded text-center">
                        <div className="text-2xl mb-2">🎵</div>
                        <div className="text-sm">Music</div>
                      </div>
                      <div className="bg-gray-800 p-4 rounded text-center">
                        <div className="text-2xl mb-2">📍</div>
                        <div className="text-sm">Navigation</div>
                      </div>
                      <div className="bg-gray-800 p-4 rounded text-center">
                        <div className="text-2xl mb-2">📞</div>
                        <div className="text-sm">Phone</div>
                      </div>
                    </div>

                    {/* Highlight problematic element */}
                    <div className="relative">
                      {selectedIssue.ui_preview?.element_type === 'button' && (
                        <div className="absolute border-4 border-red-500 bg-red-500 bg-opacity-20 rounded p-2">
                          <div className="bg-red-600 text-white text-xs px-2 py-1 rounded mb-2">
                            Accessibility Issue: {selectedIssue.wcag_guideline}
                          </div>
                          <button className="bg-blue-600 px-4 py-2 rounded text-sm">
                            Problematic Button
                          </button>
                        </div>
                      )}

                      {selectedIssue.ui_preview?.element_type === 'img' && (
                        <div className="absolute border-4 border-red-500 bg-red-500 bg-opacity-20 rounded p-2">
                          <div className="bg-red-600 text-white text-xs px-2 py-1 rounded mb-2">
                            Missing Alt Text: {selectedIssue.wcag_guideline}
                          </div>
                          <div className="bg-gray-600 w-20 h-20 rounded flex items-center justify-center">
                            🖼️
                          </div>
                        </div>
                      )}

                      {!selectedIssue.ui_preview?.element_type && (
                        <div className="border-4 border-red-500 bg-red-500 bg-opacity-20 rounded p-4">
                          <div className="bg-red-600 text-white text-xs px-2 py-1 rounded mb-2">
                            Accessibility Issue Found
                          </div>
                          <p className="text-sm">
                            The highlighted area contains an accessibility violation related to {selectedIssue.category} principles.
                          </p>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded">
                    <h4 className="font-semibold text-yellow-800 mb-2">Impact on Users</h4>
                    <p className="text-yellow-700 text-sm">{selectedIssue.impact || "This issue may prevent users with disabilities from effectively using the infotainment system."}</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Modal Footer */}
          <div className="flex justify-between items-center p-4 border-t bg-gray-50">
            <div className="flex gap-2">
              <span className={`px-2 py-1 rounded text-xs border ${getSeverityColor(selectedIssue.severity)}`}>
                Level {selectedIssue.severity}
              </span>
              <span className={`px-2 py-1 rounded text-xs ${getCategoryColor(selectedIssue.category)}`}>
                {selectedIssue.category}
              </span>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setShowIssueModal(false)}
                className="px-4 py-2 text-gray-600 border border-gray-300 rounded hover:bg-gray-50"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Configuration Page Component
  const ConfigurationPage = () => (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Infotainment Accessibility Analyzer
              </h1>
              <p className="text-gray-600 mt-1">
                Detect WCAG 2.2 compliance issues using multiple LLMs
              </p>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Configuration Panel */}
        <div className="bg-white rounded-lg shadow p-8">
          <h2 className="text-2xl font-semibold mb-8 flex items-center gap-3">
            <Settings size={28} />
            Upload Files and Configure Analysis
          </h2>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* File Upload Section */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Upload Files</h3>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".html,.htm,.css,.js,.jsx,.ts,.tsx,.xml,.cpp,.c,.h,.java,.kt,.swift,.zip"
                onChange={handleFileUpload}
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                className="w-full flex items-center justify-center gap-3 px-6 py-8 border-2 border-dashed border-gray-300 rounded-lg hover:border-gray-400 transition-colors text-lg"
                disabled={loading}
              >
                <Upload size={32} />
                <div>
                  <div className="font-medium">
                    {loading ? 'Uploading...' : 'Choose Files or ZIP'}
                  </div>
                  <div className="text-sm text-gray-500">
                    Supports HTML, CSS, JS, XML, C++, Java, Swift
                  </div>
                </div>
              </button>

              {/* Uploaded Files List */}
              {files.length > 0 && (
                <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                  <h4 className="font-medium text-gray-900 mb-3">Uploaded Files ({files.length})</h4>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {files.map((file, index) => (
                      <div key={index} className="flex items-center gap-2 text-sm bg-white p-2 rounded">
                        <FileText size={16} className="text-gray-500" />
                        <span className="truncate flex-1">{file.name}</span>
                        <span className="text-gray-400">({Math.round(file.size / 1024)}KB)</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Model Selection and Analysis Section */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Select LLM Models for Analysis</h3>
              <div className="space-y-4 mb-6">
                {availableModels.map(model => (
                  <label key={model.id} className="flex items-start gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedModels.includes(model.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedModels([...selectedModels, model.id]);
                        } else {
                          setSelectedModels(selectedModels.filter(m => m !== model.id));
                        }
                      }}
                      className="mt-1 w-4 h-4"
                    />
                    <div className="flex-1">
                      <div className="font-medium text-gray-900">{model.name}</div>
                      <div className="text-sm text-gray-600">{model.description}</div>
                    </div>
                  </label>
                ))}
              </div>

              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg mb-6">
                <h4 className="font-medium text-blue-900 mb-2">Analysis Configuration</h4>
                <div className="text-sm text-blue-800 space-y-1">
                  <div>Files: {files.length} uploaded</div>
                  <div>Models: {selectedModels.length} selected</div>
                  <div>Mode: Detection + Enhanced Remediation</div>
                </div>
              </div>

              {/* Start Analysis Button */}
              <button
                onClick={handleAnalysis}
                disabled={!sessionId || selectedModels.length === 0 || loading}
                className="w-full flex items-center justify-center gap-3 px-6 py-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-lg font-medium transition-colors"
              >
                <Play size={24} />
                {loading ? 'Analyzing for WCAG 2.2 Compliance...' : 'Start Accessibility Analysis'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  // Results Page Component
  const ResultsPage = () => (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center gap-4">
              <button
                onClick={goBackToConfiguration}
                className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900 transition-colors"
              >
                <ArrowLeft size={20} />
                Back to Configuration
              </button>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">
                  Analysis Results
                </h1>
                <p className="text-gray-600 mt-1">
                  WCAG 2.2 compliance analysis using {selectedModels.join(', ')}
                </p>
              </div>
            </div>
            <div className="flex gap-3">
              <button
                onClick={downloadFixedCode}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                <Download size={20} />
                Download Fixed Code
              </button>
              <button
                onClick={downloadReport}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                <FileText size={20} />
                Download Report
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-6">
          {/* Results Summary */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Analysis Summary</h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {Object.entries(analysisResults).map(([model, results]) => {
                const totalIssues = Array.isArray(results)
                  ? results.reduce((sum, file) => sum + (file.issues?.length || 0), 0)
                  : 0;

                return (
                  <div key={model} className="bg-gray-50 rounded-lg p-4">
                    <h3 className="font-medium text-gray-900">{model}</h3>
                    <div className="text-2xl font-bold text-blue-600 mt-1">
                      {totalIssues}
                    </div>
                    <div className="text-sm text-gray-600">issues found</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Issues List */}
          <div className="bg-white rounded-lg shadow">
            <div className="p-6 border-b">
              <h2 className="text-xl font-semibold">Detected Issues</h2>
              <p className="text-gray-600 mt-1">
                Click "Smart Fix" to preview AI-powered remediation, or "View" for details
              </p>
            </div>

            <div className="divide-y">
              {getAllIssues().map((issue, index) => (
                <div key={index} className="p-6 hover:bg-gray-50">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="font-medium text-gray-900">
                          {issue.wcag_guideline}
                        </h3>
                        <span className={`px-2 py-1 rounded text-xs border ${getSeverityColor(issue.severity)}`}>
                          Level {issue.severity}
                        </span>
                        <span className={`px-2 py-1 rounded text-xs ${getCategoryColor(issue.category)}`}>
                          {issue.category}
                        </span>
                        <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                          {issue.model}
                        </span>

                        {/* Risk indicators */}
                        {issue.infotainment_risk === 'critical' && (
                          <span className="text-xs bg-red-100 text-red-800 px-2 py-1 rounded flex items-center gap-1">
                            <AlertTriangle size={12} />
                            Critical Risk
                          </span>
                        )}

                        {issue.driver_safety_impact === 'critical' && (
                          <span className="text-xs bg-orange-100 text-orange-800 px-2 py-1 rounded flex items-center gap-1">
                            <Shield size={12} />
                            Safety Critical
                          </span>
                        )}
                      </div>

                      <p className="text-gray-700 mb-2">{issue.description}</p>

                      <div className="flex items-center gap-4 text-sm text-gray-500">
                        <span>📁 {issue.fileName}</span>
                        {issue.line_numbers && (
                          <span>📍 Lines {issue.line_numbers.join(', ')}</span>
                        )}
                        {issue.validation_score && (
                          <span>🎯 Confidence: {(issue.validation_score * 100).toFixed(0)}%</span>
                        )}
                      </div>
                    </div>

                    <div className="flex gap-2 ml-4">
                      <button
                        onClick={() => openIssueModal(issue, issue.model, issue.fileName)}
                        className="flex items-center gap-1 px-3 py-2 text-blue-600 border border-blue-600 rounded hover:bg-blue-50 transition-colors"
                      >
                        <Eye size={16} />
                        View
                      </button>

                      {/* Enhanced Fix Button with Model Selection */}
                      <div className="relative group">
                        <button className="flex items-center gap-1 px-3 py-2 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded hover:from-green-700 hover:to-emerald-700 transition-all">
                          <Zap size={16} />
                          Smart Fix
                        </button>

                        {/* Dropdown for model selection */}
                        <div className="absolute right-0 top-full mt-1 w-56 bg-white border border-gray-200 rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
                          <div className="p-3">
                            <div className="text-xs text-gray-500 mb-2 font-medium">Choose AI model for remediation:</div>
                            {availableModels.map(model => (
                              <button
                                key={model.id}
                                onClick={() => handleRemediationPreview(issue.issue_id, model.id, issue)}
                                className="block w-full text-left px-3 py-2 text-sm hover:bg-gray-100 rounded transition-colors"
                              >
                                <div className="font-medium">{model.name}</div>
                                <div className="text-xs text-gray-500">{model.description}</div>
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Show applied remediation if available */}
                  {appliedRemediations[issue.issue_id] && (
                    <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-green-800 font-medium">
                          <CheckCircle size={16} />
                          <span>Fix Applied Successfully</span>
                          <span className="text-xs bg-green-100 px-2 py-1 rounded">
                            Quality: {(appliedRemediations[issue.issue_id].quality_score * 100).toFixed(0)}%
                          </span>
                        </div>
                        <button
                          onClick={() => handleRemediationRollback(issue.issue_id)}
                          className="flex items-center gap-1 px-3 py-1 text-orange-600 hover:text-orange-700 text-sm transition-colors"
                        >
                          <Undo size={14} />
                          Rollback
                        </button>
                      </div>
                      <p className="text-green-700 text-sm mt-1">
                        {appliedRemediations[issue.issue_id].changes_applied || 0} changes applied by {appliedRemediations[issue.issue_id].model}
                      </p>
                    </div>
                  )}

                  {/* Show preview if available but not applied */}
                  {remediationPreviews[issue.issue_id] && !appliedRemediations[issue.issue_id] && (
                    <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-blue-800 font-medium">
                          <Eye size={16} />
                          <span>Remediation Preview Available</span>
                          <span className="text-xs bg-blue-100 px-2 py-1 rounded">
                            Quality: {(remediationPreviews[issue.issue_id].quality_score * 100).toFixed(0)}%
                          </span>
                        </div>
                        <button
                          onClick={() => {
                            setCurrentRemediation({
                              issueId: issue.issue_id,
                              model: remediationPreviews[issue.issue_id].model,
                              issue: issue,
                              preview: remediationPreviews[issue.issue_id]
                            });
                            setShowRemediationModal(true);
                          }}
                          className="flex items-center gap-1 px-3 py-1 text-blue-600 hover:text-blue-700 text-sm transition-colors"
                        >
                          <RefreshCw size={14} />
                          Review Fix
                        </button>
                      </div>
                      <p className="text-blue-700 text-sm mt-1">
                        {remediationPreviews[issue.issue_id].changes?.length || 0} changes proposed by {remediationPreviews[issue.issue_id].model}
                      </p>
                    </div>
                  )}
                </div>
              ))}

              {getAllIssues().length === 0 && (
                <div className="p-8 text-center text-gray-500">
                  <CheckCircle size={48} className="mx-auto text-green-500 mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No accessibility issues found!</h3>
                  <p>Your infotainment interface meets WCAG 2.2 compliance standards. Great job! 🎉</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div>
      {/* Render different pages based on current state */}
      {currentPage === 'configuration' ? <ConfigurationPage /> : <ResultsPage />}

      {/* Issue Detail Modal */}
      {renderIssueModal()}

      {/* Enhanced Remediation Modal */}
      {renderRemediationModal()}

      {/* Loading Overlay */}
      {loading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 flex items-center gap-3">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
            <span>Processing...</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;