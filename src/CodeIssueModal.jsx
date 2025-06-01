import React, { useState, useEffect, useRef } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  Button,
  Alert,
  AlertIcon,
  Code,
  IconButton,
  useToast
} from '@chakra-ui/react';
import Editor from '@monaco-editor/react';
import {
  ViewIcon,
  WarningIcon,
  InfoIcon,
  ExternalLinkIcon,
  CopyIcon,
  EditIcon
} from '@chakra-ui/icons';

// Helper function to detect file language for Monaco Editor
const detectLanguage = (filename) => {
  const ext = filename.split('.').pop()?.toLowerCase();
  const languageMap = {
    'js': 'javascript',
    'jsx': 'javascript',
    'ts': 'typescript',
    'tsx': 'typescript',
    'html': 'html',
    'htm': 'html',
    'css': 'css',
    'scss': 'scss',
    'sass': 'sass',
    'json': 'json',
    'xml': 'xml',
    'qml': 'javascript', // Treat QML similar to JS for syntax highlighting
    'cpp': 'cpp',
    'c': 'c',
    'h': 'cpp',
    'hpp': 'cpp',
    'swift': 'swift',
    'kt': 'kotlin',
    'java': 'java'
  };
  return languageMap[ext] || 'plaintext';
};

// Helper function to determine if file can be rendered as web preview
const canRenderAsWeb = (filename) => {
  const ext = filename.split('.').pop()?.toLowerCase();
  return ['html', 'htm'].includes(ext);
};

// Helper function to create highlighting overlay
const createHighlightOverlay = (issue, previewRef) => {
  if (!previewRef.current || !issue) return;

  const iframe = previewRef.current;
  const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;

  // Remove existing highlights
  const existingHighlights = iframeDoc.querySelectorAll('.accessibility-highlight');
  existingHighlights.forEach(el => el.remove());

  // Create highlight based on issue type and code
  let targetElements = [];

  try {
    // Try to find elements based on the issue type and original code
    const { type, original_code, line } = issue;

    if (type === 'missing_alt_text' && original_code?.includes('<img')) {
      targetElements = Array.from(iframeDoc.querySelectorAll('img')).filter(img => !img.alt);
    }
    else if (type === 'missing_label' && original_code?.includes('input')) {
      targetElements = Array.from(iframeDoc.querySelectorAll('input, button, select, textarea')).filter(el =>
        !el.getAttribute('aria-label') && !el.getAttribute('aria-labelledby')
      );
    }
    else if (type === 'low_contrast' || type.includes('contrast')) {
      // Find text elements that might have contrast issues
      targetElements = Array.from(iframeDoc.querySelectorAll('p, span, div, h1, h2, h3, h4, h5, h6, a, button'));
    }
    else if (type.includes('touch') || type === 'inadequate_touch_targets') {
      targetElements = Array.from(iframeDoc.querySelectorAll('button, a, input[type="button"], input[type="submit"]'));
    }
    else if (type === 'keyboard_trap' || type === 'focus_issue') {
      targetElements = Array.from(iframeDoc.querySelectorAll('input, button, select, textarea, a[href]'));
    }
    else if (original_code) {
      // Try to find elements based on class names, IDs, or tag names from original code
      const classMatch = original_code.match(/class=['"]([^'"]+)['"]/);
      const idMatch = original_code.match(/id=['"]([^'"]+)['"]/);
      const tagMatch = original_code.match(/<(\w+)/);

      if (classMatch) {
        targetElements = Array.from(iframeDoc.getElementsByClassName(classMatch[1]));
      } else if (idMatch) {
        const element = iframeDoc.getElementById(idMatch[1]);
        if (element) targetElements = [element];
      } else if (tagMatch) {
        targetElements = Array.from(iframeDoc.getElementsByTagName(tagMatch[1]));
      }
    }

    // If we couldn't find specific elements, highlight the first interactive element
    if (targetElements.length === 0) {
      targetElements = Array.from(iframeDoc.querySelectorAll('button, input, a, select, textarea')).slice(0, 1);
    }

    // Create highlight overlays
    targetElements.slice(0, 3).forEach((element, index) => { // Limit to 3 elements
      const rect = element.getBoundingClientRect();
      const scrollTop = iframeDoc.documentElement.scrollTop || iframeDoc.body.scrollTop;
      const scrollLeft = iframeDoc.documentElement.scrollLeft || iframeDoc.body.scrollLeft;

      const highlight = iframeDoc.createElement('div');
      highlight.className = 'accessibility-highlight';
      highlight.style.cssText = `
        position: absolute;
        top: ${rect.top + scrollTop - 4}px;
        left: ${rect.left + scrollLeft - 4}px;
        width: ${rect.width + 8}px;
        height: ${rect.height + 8}px;
        border: 3px solid #ff4444;
        background: rgba(255, 68, 68, 0.1);
        border-radius: 4px;
        pointer-events: none;
        z-index: 10000;
        box-shadow: 0 0 10px rgba(255, 68, 68, 0.5);
        animation: pulse 2s infinite;
      `;

      // Add pulsing animation
      if (!iframeDoc.querySelector('#highlight-styles')) {
        const style = iframeDoc.createElement('style');
        style.id = 'highlight-styles';
        style.textContent = `
          @keyframes pulse {
            0%, 100% { opacity: 0.7; transform: scale(1); }
            50% { opacity: 1; transform: scale(1.02); }
          }
        `;
        iframeDoc.head.appendChild(style);
      }

      // Add tooltip
      const tooltip = iframeDoc.createElement('div');
      tooltip.className = 'accessibility-tooltip';
      tooltip.style.cssText = `
        position: absolute;
        top: ${rect.top + scrollTop - 40}px;
        left: ${rect.left + scrollLeft}px;
        background: #333;
        color: white;
        padding: 8px 12px;
        border-radius: 4px;
        font-size: 12px;
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        white-space: nowrap;
        z-index: 10001;
        pointer-events: none;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      `;
      tooltip.textContent = `${issue.type.replace(/_/g, ' ').toUpperCase()}: ${issue.description.slice(0, 50)}...`;

      iframeDoc.body.appendChild(highlight);
      iframeDoc.body.appendChild(tooltip);

      // Scroll to first highlight
      if (index === 0) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    });

  } catch (error) {
    console.error('Error creating highlight overlay:', error);
  }
};

// Main Component
const CodeIssueModal = ({ isOpen, onClose, issue, fileContent, allFileContents }) => {
  const [activeTab, setActiveTab] = useState(0);
  const [previewContent, setPreviewContent] = useState('');
  const [isPreviewReady, setIsPreviewReady] = useState(false);
  const [highlightApplied, setHighlightApplied] = useState(false);
  const previewRef = useRef(null);
  const editorRef = useRef(null);
  const toast = useToast();

  // Prepare preview content when modal opens
  useEffect(() => {
    if (isOpen && issue && allFileContents) {
      preparePreviewContent();
    }
  }, [isOpen, issue, allFileContents]);

  // Apply highlighting when preview is ready and tab is active
  useEffect(() => {
    if (isPreviewReady && activeTab === 1 && issue && !highlightApplied) {
      setTimeout(() => {
        createHighlightOverlay(issue, previewRef);
        setHighlightApplied(true);
      }, 500); // Give iframe time to fully load
    }
  }, [isPreviewReady, activeTab, issue, highlightApplied]);

  // Reset highlight state when issue changes
  useEffect(() => {
    setHighlightApplied(false);
  }, [issue]);

  const preparePreviewContent = () => {
    if (!issue || !allFileContents) return;

    const filename = issue.file;

    // Check if this is an HTML file
    if (canRenderAsWeb(filename)) {
      // Use the file content directly
      let htmlContent = allFileContents[filename] || fileContent;

      // Inject CSS and JS files if they exist
      const cssFiles = Object.keys(allFileContents).filter(f => f.endsWith('.css'));
      const jsFiles = Object.keys(allFileContents).filter(f => f.endsWith('.js') && !f.includes('min.js'));

      // Add CSS
      let cssIncludes = '';
      cssFiles.forEach(cssFile => {
        cssIncludes += `<style>/* ${cssFile} */\n${allFileContents[cssFile]}\n</style>\n`;
      });

      // Add JS (be careful with execution)
      let jsIncludes = '';
      jsFiles.slice(0, 2).forEach(jsFile => { // Limit to 2 JS files for safety
        jsIncludes += `<script>/* ${jsFile} - Limited execution for preview */\n// ${allFileContents[jsFile].slice(0, 1000)}...\n</script>\n`;
      });

      // Create complete HTML document if it's just a fragment
      if (!htmlContent.includes('<html')) {
        htmlContent = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Infotainment Preview - ${filename}</title>
    <style>
        body { 
            margin: 0; 
            padding: 20px; 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f0f0f0;
        }
        /* Infotainment-like styling */
        .dashboard { background: linear-gradient(135deg, #1a1a1a, #2d2d2d); color: white; }
        .navigation { background: linear-gradient(135deg, #0066cc, #004499); color: white; }
        .media { background: linear-gradient(135deg, #cc6600, #994400); color: white; }
        button { 
            padding: 12px 24px; 
            margin: 8px; 
            border: none; 
            border-radius: 6px; 
            cursor: pointer;
            font-size: 16px;
            transition: all 0.2s;
        }
        button:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
        input, select { 
            padding: 12px; 
            margin: 8px; 
            border: 2px solid #ddd; 
            border-radius: 6px;
            font-size: 16px;
        }
        .touch-target { min-width: 44px; min-height: 44px; } /* Automotive touch targets */
    </style>
    ${cssIncludes}
</head>
<body>
    ${htmlContent}
    ${jsIncludes}
</body>
</html>`;
      } else {
        // Insert CSS into existing HTML
        htmlContent = htmlContent.replace('</head>', `${cssIncludes}</head>`);
        htmlContent = htmlContent.replace('</body>', `${jsIncludes}</body>`);
      }

      setPreviewContent(htmlContent);
    } else {
      // For non-HTML files, create a visual representation
      setPreviewContent(`
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Structure Preview - ${filename}</title>
    <style>
        body { 
            margin: 0; 
            padding: 20px; 
            font-family: monospace; 
            background: #f8f9fa;
            font-size: 14px;
            line-height: 1.5;
        }
        .code-preview {
            background: white;
            border: 1px solid #e1e5e9;
            border-radius: 6px;
            padding: 20px;
            white-space: pre-wrap;
            overflow: auto;
            max-height: 80vh;
        }
        .highlight-line {
            background: #fff3cd;
            padding: 2px 4px;
            margin: 0 -4px;
            border-left: 4px solid #ffc107;
        }
        .issue-marker {
            background: #f8d7da;
            border-left: 4px solid #dc3545;
            padding: 2px 4px;
            margin: 0 -4px;
        }
    </style>
</head>
<body>
    <div class="code-preview">
        <h3>File: ${filename}</h3>
        <p><strong>Issue Type:</strong> ${issue.type.replace(/_/g, ' ')}</p>
        <p><strong>Line:</strong> ${issue.line}</p>
        <p><strong>Description:</strong> ${issue.description}</p>
        <hr>
        <div class="code-content">
            ${fileContent.split('\n').map((line, index) => 
              `<div class="${index + 1 === issue.line ? 'issue-marker' : ''}">${index + 1}: ${line.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>`
            ).join('')}
        </div>
    </div>
</body>
</html>`);
    }
  };

  const handleEditorMount = (editor, monaco) => {
    editorRef.current = editor;

    // Jump to issue line
    if (issue?.line) {
      setTimeout(() => {
        editor.revealLineInCenter(issue.line);
        editor.setPosition({ lineNumber: issue.line, column: 1 });

        // Highlight the issue line
        editor.deltaDecorations([], [{
          range: new monaco.Range(issue.line, 1, issue.line, 1),
          options: {
            isWholeLine: true,
            className: 'issue-line-highlight',
            glyphMarginClassName: 'issue-line-glyph'
          }
        }]);
      }, 100);
    }
  };

  const handlePreviewLoad = () => {
    setIsPreviewReady(true);
  };

  const copyIssueDetails = () => {
    const details = `
File: ${issue.file}
Line: ${issue.line}
Type: ${issue.type.replace(/_/g, ' ')}
Severity: ${issue.severity}
Description: ${issue.description}
Standards: ${[
  ...(issue.wcag_criteria || []).map(c => `WCAG ${c}`),
  ...(issue.iso15008_criteria || []).map(c => `ISO15008 ${c}`),
  ...(issue.nhtsa_criteria || []).map(c => `NHTSA ${c}`)
].join(', ')}
    `.trim();

    navigator.clipboard.writeText(details);
    toast({
      title: 'Issue details copied to clipboard',
      status: 'success',
      duration: 2000
    });
  };

  if (!issue) return null;

  const getSeverityColor = (severity) => {
    const colors = {
      'safety_critical': 'red',
      'critical': 'orange',
      'high': 'yellow',
      'medium': 'blue',
      'low': 'green'
    };
    return colors[severity] || 'gray';
  };

  return (
    <>
      {/* Add CSS for editor highlighting */}
      <style>
        {`
          .issue-line-highlight {
            background: rgba(255, 68, 68, 0.1) !important;
            border-left: 4px solid #ff4444 !important;
          }
          .issue-line-glyph {
            background: #ff4444 !important;
            width: 4px !important;
          }
        `}
      </style>

      <Modal isOpen={isOpen} onClose={onClose} size="full">
        <ModalOverlay />
        <ModalContent maxW="95vw" maxH="95vh">
          <ModalHeader>
            <HStack justify="space-between" align="start">
              <VStack align="start" spacing={2}>
                <HStack>
                  <WarningIcon color={getSeverityColor(issue.severity)} />
                  <Text fontSize="lg" fontWeight="bold">
                    {issue.type.replace(/_/g, ' ').toUpperCase()}
                  </Text>
                  <Badge colorScheme={getSeverityColor(issue.severity)}>
                    {issue.severity}
                  </Badge>
                  {issue.safety_critical && (
                    <Badge colorScheme="red" variant="solid">
                      SAFETY CRITICAL
                    </Badge>
                  )}
                </HStack>

                <HStack>
                  <Text fontSize="sm" color="gray.600">
                    <strong>File:</strong> {issue.file}
                  </Text>
                  <Text fontSize="sm" color="gray.600">
                    <strong>Line:</strong> {issue.line}
                  </Text>
                  <Text fontSize="sm" color="gray.600">
                    <strong>Model:</strong> {issue.model}
                  </Text>
                </HStack>

                <Text fontSize="sm" maxW="600px">
                  {issue.description}
                </Text>

                {/* Standards badges */}
                <HStack wrap="wrap">
                  {issue.wcag_criteria?.map((criteria, i) => (
                    <Badge key={i} colorScheme="blue" size="sm">
                      WCAG {criteria}
                    </Badge>
                  ))}
                  {issue.iso15008_criteria?.map((criteria, i) => (
                    <Badge key={i} colorScheme="green" size="sm">
                      ISO15008
                    </Badge>
                  ))}
                  {issue.nhtsa_criteria?.map((criteria, i) => (
                    <Badge key={i} colorScheme="orange" size="sm">
                      NHTSA
                    </Badge>
                  ))}
                </HStack>
              </VStack>

              <HStack>
                <IconButton
                  icon={<CopyIcon />}
                  onClick={copyIssueDetails}
                  variant="outline"
                  size="sm"
                  title="Copy issue details"
                />
                <ModalCloseButton position="static" />
              </HStack>
            </HStack>
          </ModalHeader>

          <ModalBody p={0} flex="1" overflow="hidden">
            <Tabs
              index={activeTab}
              onChange={setActiveTab}
              height="100%"
              display="flex"
              flexDirection="column"
            >
              <TabList px={6} pt={2}>
                <Tab>
                  <HStack>
                    <EditIcon />
                    <Text>Code View</Text>
                  </HStack>
                </Tab>
                <Tab isDisabled={!canRenderAsWeb(issue.file) && !previewContent}>
                  <HStack>
                    <ViewIcon />
                    <Text>Interface Preview</Text>
                  </HStack>
                </Tab>
              </TabList>

              <TabPanels flex="1" overflow="hidden">
                {/* Code View Tab */}
                <TabPanel p={0} height="100%">
                  <VStack spacing={0} height="100%">
                    {/* Suggested fix section */}
                    {issue.suggested_fix && (
                      <Box width="100%" bg="green.50" p={4} borderBottom="1px solid" borderColor="gray.200">
                        <VStack align="start" spacing={2}>
                          <Text fontWeight="bold" color="green.800">
                            💡 Suggested Fix:
                          </Text>
                          <Code
                            p={3}
                            bg="green.100"
                            color="green.800"
                            borderRadius="md"
                            width="100%"
                            whiteSpace="pre-wrap"
                            fontSize="sm"
                          >
                            {issue.suggested_fix}
                          </Code>
                        </VStack>
                      </Box>
                    )}

                    {/* Editor */}
                    <Box flex="1" width="100%">
                      <Editor
                        height="100%"
                        language={detectLanguage(issue.file)}
                        value={fileContent}
                        onMount={handleEditorMount}
                        options={{
                          readOnly: true,
                          minimap: { enabled: true },
                          wordWrap: 'on',
                          lineNumbers: 'on',
                          scrollBeyondLastLine: false,
                          automaticLayout: true,
                          fontSize: 14,
                          lineHeight: 20,
                          glyphMargin: true
                        }}
                        theme="vs-light"
                      />
                    </Box>
                  </VStack>
                </TabPanel>

                {/* Interface Preview Tab */}
                <TabPanel p={0} height="100%">
                  <VStack spacing={0} height="100%">
                    {/* Instructions */}
                    <Alert status="info" borderRadius={0}>
                      <AlertIcon />
                      <HStack justify="space-between" width="100%">
                        <Text fontSize="sm">
                          {canRenderAsWeb(issue.file)
                            ? "Live infotainment interface preview with issue highlighted in red"
                            : "Code structure preview showing the issue location"
                          }
                        </Text>
                        <Button
                          size="sm"
                          leftIcon={<ExternalLinkIcon />}
                          onClick={() => {
                            if (previewRef.current) {
                              const newWindow = window.open();
                              newWindow.document.write(previewContent);
                              newWindow.document.close();
                            }
                          }}
                        >
                          Open in New Window
                        </Button>
                      </HStack>
                    </Alert>

                    {/* Preview iframe */}
                    <Box flex="1" width="100%" position="relative">
                      {previewContent ? (
                        <iframe
                          ref={previewRef}
                          srcDoc={previewContent}
                          style={{
                            width: '100%',
                            height: '100%',
                            border: 'none',
                            background: 'white'
                          }}
                          onLoad={handlePreviewLoad}
                          sandbox="allow-same-origin allow-scripts"
                          title={`Preview of ${issue.file}`}
                        />
                      ) : (
                        <Box
                          display="flex"
                          alignItems="center"
                          justifyContent="center"
                          height="100%"
                          bg="gray.50"
                        >
                          <VStack>
                            <InfoIcon boxSize={8} color="gray.400" />
                            <Text color="gray.500">
                              Preview not available for {issue.file}
                            </Text>
                          </VStack>
                        </Box>
                      )}
                    </Box>
                  </VStack>
                </TabPanel>
              </TabPanels>
            </Tabs>
          </ModalBody>
        </ModalContent>
      </Modal>
    </>
  );
};

export default CodeIssueModal;