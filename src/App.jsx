import React, { useState, useEffect } from 'react';
import {
  ChakraProvider,
  Box,
  VStack,
  HStack,
  Text,
  Button,
  Input,
  useToast,
  Progress,
  Badge,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  useDisclosure,
  FormControl,
  FormLabel,
  Checkbox,
  CheckboxGroup,
  Stack,
  Card,
  CardBody,
  CardHeader,
  Heading,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Icon,
  Flex,
  Spacer,
  Tag,
  TagLabel,
  Wrap,
  WrapItem,
  Code,
  Spinner,
  CircularProgress,
  CircularProgressLabel,
  Skeleton,
  SkeletonText,
  IconButton
} from '@chakra-ui/react';
import { WarningIcon, CheckIcon, DownloadIcon, RepeatIcon, InfoIcon, ViewIcon } from '@chakra-ui/icons';

// Import the new CodeIssueModal component
import CodeIssueModal from './CodeIssueModal';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Default/fallback data to show immediately while loading
const DEFAULT_MODELS = [
  {
    id: "gpt-4o",
    name: "GPT-4o",
    provider: "OpenAI",
    description: "Advanced reasoning and code analysis",
    capabilities: ["Code review", "WCAG compliance", "Automotive safety analysis"]
  },
  {
    id: "claude-opus-4",
    name: "Claude Opus 4",
    provider: "Anthropic",
    description: "Balanced performance for accessibility analysis",
    capabilities: ["Accessibility review", "Standards compliance", "Detailed explanations"]
  },
  {
    id: "Deepseek-V3",
    name: "DeepSeek V3",
    provider: "DeepSeek",
    description: "Specialized code analysis and debugging",
    capabilities: ["Code optimization", "Bug detection", "Performance analysis"]
  },
  {
    id: "llama-maverick",
    name: "Llama Maverick",
    provider: "Meta/Replicate",
    description: "Latest Llama model with enhanced automotive domain knowledge",
    capabilities: ["Automotive UI analysis", "Safety-critical code review", "Multi-modal understanding"]
  }
];

const DEFAULT_STANDARDS = [
  {
    id: "WCAG 2.2",
    name: "Web Content Accessibility Guidelines 2.2",
    description: "International standard for web accessibility",
    category: "Web Standards",
    applicable_to: ["HTML", "CSS", "JavaScript", "Web-based HMI"]
  },
  {
    id: "ISO15008",
    name: "ISO 15008:2017",
    description: "Road vehicles — Ergonomic aspects of transport information and control systems",
    category: "Automotive Standards",
    applicable_to: ["All infotainment interfaces"]
  },
  {
    id: "NHTSA",
    name: "NHTSA Driver Distraction Guidelines",
    description: "US safety guidelines for in-vehicle electronic devices",
    category: "Safety Standards",
    applicable_to: ["All driver-accessible interfaces"]
  },
  {
    id: "SAE J3016",
    name: "SAE J3016 Levels of Driving Automation",
    description: "Standard for automotive automation levels",
    category: "Automation Standards",
    applicable_to: ["Automated driving systems"]
  },
  {
    id: "GTR8",
    name: "Global Technical Regulation No. 8",
    description: "UN regulation for Electronic Stability Control systems",
    category: "International Standards",
    applicable_to: ["Safety-critical automotive systems"]
  }
];

// Loading skeleton component
const LoadingSkeleton = ({ type = 'card', lines = 3 }) => {
  if (type === 'card') {
    return (
      <Card>
        <CardHeader>
          <Skeleton height="20px" width="60%" />
        </CardHeader>
        <CardBody>
          <VStack spacing={3} align="stretch">
            {Array.from({ length: lines }, (_, i) => (
              <Skeleton key={i} height="15px" width={i === lines - 1 ? "80%" : "100%"} />
            ))}
          </VStack>
        </CardBody>
      </Card>
    );
  }

  if (type === 'checkbox') {
    return (
      <HStack spacing={3}>
        <Skeleton height="16px" width="16px" />
        <VStack align="start" spacing={1} flex="1">
          <Skeleton height="16px" width="60%" />
          <Skeleton height="12px" width="80%" />
        </VStack>
      </HStack>
    );
  }

  return <Skeleton height="20px" />;
};

// Connection status indicator
const ConnectionStatus = ({ isLoading, hasError }) => {
  if (isLoading) {
    return (
      <HStack spacing={2}>
        <Spinner size="xs" />
        <Text fontSize="xs" color="gray.500">Loading...</Text>
      </HStack>
    );
  }

  if (hasError) {
    return (
      <HStack spacing={2}>
        <Box w="6px" h="6px" bg="orange.400" borderRadius="full" />
        <Text fontSize="xs" color="orange.500">Using cached data</Text>
      </HStack>
    );
  }

  return (
    <HStack spacing={2}>
      <Box w="6px" h="6px" bg="green.400" borderRadius="full" />
      <Text fontSize="xs" color="green.500">Connected</Text>
    </HStack>
  );
};

function App() {
  // Authentication state
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(null);
  const [isRegistering, setIsRegistering] = useState(false);

  // Modal controls
  const { isOpen: isLoginOpen, onOpen: onLoginOpen, onClose: onLoginClose } = useDisclosure();
  const { isOpen: isCodeModalOpen, onOpen: onCodeModalOpen, onClose: onCodeModalClose } = useDisclosure();

  // Application state
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [analysisStatus, setAnalysisStatus] = useState('');
  const [issues, setIssues] = useState([]);
  const [infotainmentInsights, setInfotainmentInsights] = useState(null);
  const [analyses, setAnalyses] = useState([]);
  const [currentAnalysis, setCurrentAnalysis] = useState(null);

  // Configuration state
  const [selectedModels, setSelectedModels] = useState([]);
  const [selectedStandards, setSelectedStandards] = useState(['WCAG 2.2', 'ISO15008', 'NHTSA']);

  // Fix tracking state
  const [appliedFixes, setAppliedFixes] = useState(new Set());
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Available options with loading states
  const [availableModels, setAvailableModels] = useState(DEFAULT_MODELS);
  const [availableStandards, setAvailableStandards] = useState(DEFAULT_STANDARDS);
  const [modelsLoading, setModelsLoading] = useState(true);
  const [standardsLoading, setStandardsLoading] = useState(true);
  const [dataLoaded, setDataLoaded] = useState(false);
  const [connectionError, setConnectionError] = useState(false);

  // Upload progress state
  const [uploadProgress, setUploadProgress] = useState(null);
  const [filteringStats, setFilteringStats] = useState(null);

  // Code modal state
  const [selectedIssue, setSelectedIssue] = useState(null);
  const [selectedFileContent, setSelectedFileContent] = useState('');

  const toast = useToast();

  // Function to open code modal with issue details
  const openCodeModal = (issue) => {
    if (!currentAnalysis?.file_contents) {
      toast({
        title: 'File content not available',
        description: 'Please reload the analysis to view code',
        status: 'warning'
      });
      return;
    }

    const fileContent = currentAnalysis.file_contents[issue.file];
    if (!fileContent) {
      toast({
        title: 'File not found',
        description: `Could not find content for ${issue.file}`,
        status: 'error'
      });
      return;
    }

    setSelectedIssue(issue);
    setSelectedFileContent(fileContent);
    onCodeModalOpen();
  };

  // Initial data loading with better error handling
  useEffect(() => {
    const initializeApp = async () => {
      if (token) {
        try {
          // First validate token with a quick request
          const response = await fetch(`${API_URL}/analyses`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });

          if (response.status === 401) {
            console.log('Invalid token detected, clearing...');
            logout();
            toast({
              title: 'Session expired - please login again',
              status: 'info',
              duration: 5000
            });
            return;
          }

          if (response.ok) {
            // Load all data in parallel with timeout
            const loadDataWithTimeout = (promise, timeout = 10000) => {
              return Promise.race([
                promise,
                new Promise((_, reject) =>
                  setTimeout(() => reject(new Error('Request timeout')), timeout)
                )
              ]);
            };

            const results = await Promise.allSettled([
              loadDataWithTimeout(fetchAvailableModels()),
              loadDataWithTimeout(fetchAvailableStandards()),
              loadDataWithTimeout(fetchAnalyses())
            ]);

            // Check if any critical requests failed
            const hasFailures = results.some(result => result.status === 'rejected');
            if (hasFailures) {
              setConnectionError(true);
              toast({
                title: 'Connection issues detected',
                description: 'Using cached data. Some features may be limited.',
                status: 'warning',
                duration: 8000,
                isClosable: true
              });
            }

            setDataLoaded(true);
          }
        } catch (error) {
          console.error('App initialization error:', error);
          setConnectionError(true);
          toast({
            title: 'Connection error',
            description: 'Using cached data. Please check your internet connection.',
            status: 'warning',
            duration: 8000,
            isClosable: true
          });
          // Keep using default data
          setModelsLoading(false);
          setStandardsLoading(false);
          setDataLoaded(true);
        }
      } else {
        // No token, stop loading states immediately
        setModelsLoading(false);
        setStandardsLoading(false);
        setDataLoaded(true);
      }
    };

    // Small delay to prevent flash, then initialize
    const timer = setTimeout(initializeApp, 500);
    return () => clearTimeout(timer);
  }, [token]);

  // Logout with cleanup
  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    setAnalyses([]);
    setCurrentAnalysis(null);
    setIssues([]);
    setAnalysisStatus('');
    setInfotainmentInsights(null);
    setFiles([]);
    setSelectedModels([]);
    setAppliedFixes(new Set());
    setHasUnsavedChanges(false);
    setUploadProgress(null);
    setFilteringStats(null);
    setDataLoaded(true);
    setModelsLoading(false);
    setStandardsLoading(false);
    setConnectionError(false);
  };

  // Enhanced authentication functions
  const handleAuth = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const email = formData.get('email');
    const password = formData.get('password');

    if (!email || !password) {
      toast({ title: 'Please enter both email and password', status: 'error' });
      return;
    }

    try {
      setLoading(true);
      const endpoint = isRegistering ? '/register' : '/login';
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      const data = await response.json();

      if (response.ok) {
        setToken(data.token);
        localStorage.setItem('token', data.token);
        setUser({ id: data.user_id, email });
        onLoginClose();

        // Reset loading states for fresh data fetch
        setModelsLoading(true);
        setStandardsLoading(true);
        setDataLoaded(false);
        setConnectionError(false);

        try {
          await Promise.allSettled([
            fetchAvailableModels(),
            fetchAvailableStandards(),
            fetchAnalyses()
          ]);

          setDataLoaded(true);

          toast({
            title: isRegistering ? 'Registration successful!' : 'Login successful!',
            status: 'success'
          });
        } catch (verifyError) {
          console.error('Post-auth data fetch failed:', verifyError);
          setConnectionError(true);
          toast({
            title: 'Login successful, but connection issues detected',
            description: 'Using cached data - some features may be limited',
            status: 'warning'
          });
          setDataLoaded(true);
        }
      } else {
        if (data.detail?.includes('User not found')) {
          toast({
            title: 'Session expired - please register again',
            status: 'warning'
          });
        } else if (data.detail?.includes('Email already registered')) {
          toast({
            title: 'Email already registered - please login instead',
            status: 'info'
          });
          setIsRegistering(false);
        } else {
          toast({
            title: data.detail || `${isRegistering ? 'Registration' : 'Login'} failed`,
            status: 'error'
          });
        }
      }
    } catch (error) {
      console.error('Auth error:', error);
      toast({
        title: 'Network error - please check your connection',
        status: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  // Enhanced data fetching functions with better error handling
  const fetchAvailableModels = async () => {
    try {
      setModelsLoading(true);
      const response = await fetch(`${API_URL}/models`);
      if (response.ok) {
        const data = await response.json();
        setAvailableModels(data.models || DEFAULT_MODELS);
        setConnectionError(false);
      } else {
        console.warn('Failed to fetch models, using defaults');
        setAvailableModels(DEFAULT_MODELS);
        setConnectionError(true);
      }
    } catch (error) {
      console.error('Error fetching models:', error);
      setAvailableModels(DEFAULT_MODELS);
      setConnectionError(true);
    } finally {
      setModelsLoading(false);
    }
  };

  const fetchAvailableStandards = async () => {
    try {
      setStandardsLoading(true);
      const response = await fetch(`${API_URL}/standards`);
      if (response.ok) {
        const data = await response.json();
        setAvailableStandards(data.standards || DEFAULT_STANDARDS);
        setConnectionError(false);
      } else {
        console.warn('Failed to fetch standards, using defaults');
        setAvailableStandards(DEFAULT_STANDARDS);
        setConnectionError(true);
      }
    } catch (error) {
      console.error('Error fetching standards:', error);
      setAvailableStandards(DEFAULT_STANDARDS);
      setConnectionError(true);
    } finally {
      setStandardsLoading(false);
    }
  };

  const fetchAnalyses = async () => {
    if (!token) return;

    try {
      const response = await fetch(`${API_URL}/analyses`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.status === 401) {
        logout();
        return;
      }

      if (response.ok) {
        const data = await response.json();
        setAnalyses(data);
      }
    } catch (error) {
      console.error('Error fetching analyses:', error);
    }
  };

  // Enhanced file upload with progress tracking
  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files);
    setFiles(files);

    if (files.length === 0) return;

    // Calculate total size and show preliminary info
    const totalSize = files.reduce((sum, file) => sum + file.size, 0);
    const isLargeUpload = totalSize > 10 * 1024 * 1024; // 10MB+

    if (isLargeUpload) {
      setUploadProgress({
        stage: 'preparing',
        message: 'Preparing large file upload...',
        totalFiles: files.length,
        totalSizeMB: (totalSize / (1024 * 1024)).toFixed(1)
      });
    }

    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    try {
      setLoading(true);
      setAnalysisStatus('uploading');

      if (isLargeUpload) {
        setUploadProgress(prev => ({
          ...prev,
          stage: 'uploading',
          message: 'Uploading and filtering files...'
        }));
      }

      const response = await fetch(`${API_URL}/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });

      if (response.ok) {
        const data = await response.json();

        // Store filtering statistics
        setFilteringStats(data.filtering_stats);

        toast({
          title: `Files processed successfully!`,
          description: data.message,
          status: 'success',
          duration: 8000,
          isClosable: true
        });

        // Show detailed upload results if many files were processed
        if (data.skipped_files > 0) {
          setTimeout(() => {
            toast({
              title: 'File Filtering Applied',
              description: `Analyzed ${data.total_files} relevant files, skipped ${data.skipped_files} irrelevant files (node_modules, build files, etc.)`,
              status: 'info',
              duration: 10000,
              isClosable: true
            });
          }, 2000);
        }

        setCurrentAnalysis({
          id: data.analysis_id,
          files: data.files,
          infotainment_files: data.infotainment_files,
          context_type: data.context_type,
          total_files: data.total_files,
          skipped_files: data.skipped_files
        });
        setAnalysisStatus('uploaded');
        setAppliedFixes(new Set());
        setHasUnsavedChanges(false);
        fetchAnalyses();
      } else {
        const errorData = await response.json();
        if (response.status === 401) {
          toast({
            title: 'Session expired - please login again',
            status: 'warning'
          });
          logout();
        } else {
          toast({
            title: 'Upload failed',
            description: errorData.detail || 'Unknown error occurred',
            status: 'error',
            duration: 10000,
            isClosable: true
          });
        }
      }
    } catch (error) {
      console.error('Upload error:', error);
      toast({
        title: 'Network error during upload',
        description: 'Please check your connection and try again',
        status: 'error'
      });
    } finally {
      setLoading(false);
      setAnalysisStatus('');
      setUploadProgress(null);
    }
  };

  // Start analysis
  const startAnalysis = async () => {
    if (!currentAnalysis || selectedModels.length === 0) {
      toast({
        title: 'Please upload files and select at least one model',
        status: 'warning'
      });
      return;
    }

    try {
      setLoading(true);
      setAnalysisStatus('analyzing');

      const response = await fetch(`${API_URL}/analyze/${currentAnalysis.id}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          llm_models: selectedModels,
          standards: selectedStandards
        })
      });

      if (response.ok) {
        const data = await response.json();
        toast({
          title: 'Analysis started!',
          description: `Analyzing ${data.files_to_analyze} files with ${selectedModels.length} models using ${selectedStandards.length} standards`,
          status: 'info',
          duration: 8000,
          isClosable: true
        });

        pollAnalysisStatus(currentAnalysis.id);
      } else {
        const errorData = await response.json();
        if (response.status === 401) {
          logout();
        } else {
          toast({
            title: 'Analysis failed to start',
            description: errorData.detail,
            status: 'error'
          });
          setAnalysisStatus('');
        }
      }
    } catch (error) {
      console.error('Analysis error:', error);
      toast({
        title: 'Network error during analysis',
        status: 'error'
      });
      setAnalysisStatus('');
    } finally {
      setLoading(false);
    }
  };

  // Poll analysis status
  const pollAnalysisStatus = async (analysisId) => {
    const poll = async () => {
      try {
        const response = await fetch(`${API_URL}/analysis/${analysisId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.status === 401) {
          logout();
          return;
        }

        if (response.ok) {
          const data = await response.json();

          if (data.analysis.status === 'completed') {
            setIssues(data.issues || []);
            setAnalysisStatus('completed');

            setCurrentAnalysis(prev => ({
              ...prev,
              file_contents: data.file_contents
            }));

            fetchInfotainmentInsights(analysisId);

            toast({
              title: 'Analysis completed!',
              description: `Found ${data.issues?.length || 0} accessibility issues`,
              status: 'success',
              duration: 5000,
              isClosable: true
            });

            fetchAnalyses();
          } else if (data.analysis.status === 'failed') {
            setAnalysisStatus('failed');
            toast({
              title: 'Analysis failed',
              description: data.analysis.error_message || 'Unknown error',
              status: 'error'
            });
          } else {
            setTimeout(poll, 3000);
          }
        }
      } catch (error) {
        console.error('Polling error:', error);
        setTimeout(poll, 5000);
      }
    };

    poll();
  };

  // Fetch insights
  const fetchInfotainmentInsights = async (analysisId) => {
    try {
      const response = await fetch(`${API_URL}/analysis/${analysisId}/infotainment-insights`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        setInfotainmentInsights(data);
      }
    } catch (error) {
      console.error('Error fetching insights:', error);
    }
  };

  // Apply fix
  const applyFix = async (issueId) => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/issue/${issueId}/apply`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        setIssues(issues.map(issue =>
          issue.id === issueId ? { ...issue, fix_applied: true } : issue
        ));

        setAppliedFixes(prev => new Set([...prev, issueId]));
        setHasUnsavedChanges(true);

        toast({
          title: 'Fix applied successfully',
          description: 'The code has been updated with the suggested fix',
          status: 'success',
          duration: 3000
        });
      } else {
        const errorData = await response.json();
        toast({
          title: 'Failed to apply fix',
          description: errorData.detail,
          status: 'error'
        });
      }
    } catch (error) {
      console.error('Error applying fix:', error);
      toast({
        title: 'Network error',
        description: 'Failed to apply fix due to network error',
        status: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  // Undo fix
  const undoFix = async (issueId) => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/issue/${issueId}/undo`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        setIssues(issues.map(issue =>
          issue.id === issueId ? { ...issue, fix_applied: false } : issue
        ));

        setAppliedFixes(prev => {
          const newSet = new Set(prev);
          newSet.delete(issueId);
          return newSet;
        });

        const remainingFixes = appliedFixes.size - 1;
        setHasUnsavedChanges(remainingFixes > 0);

        toast({
          title: 'Fix undone successfully',
          description: 'The original code has been restored',
          status: 'success',
          duration: 3000
        });
      } else {
        const errorData = await response.json();
        toast({
          title: 'Failed to undo fix',
          description: errorData.detail,
          status: 'error'
        });
      }
    } catch (error) {
      console.error('Error undoing fix:', error);
      toast({
        title: 'Network error',
        description: 'Failed to undo fix due to network error',
        status: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  // Download updated files
  const downloadUpdatedFiles = async () => {
    if (!currentAnalysis || appliedFixes.size === 0) {
      toast({
        title: 'No fixes to download',
        description: 'Apply some fixes first before downloading',
        status: 'warning'
      });
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/analysis/${currentAnalysis.id}/download-updated`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `updated_infotainment_files_${currentAnalysis.id}.zip`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        toast({
          title: 'Updated files downloaded',
          description: `ZIP file contains ${appliedFixes.size} applied fixes`,
          status: 'success'
        });
      } else {
        const errorData = await response.json();
        toast({
          title: 'Download failed',
          description: errorData.detail,
          status: 'error'
        });
      }
    } catch (error) {
      console.error('Error downloading files:', error);
      toast({
        title: 'Download error',
        description: 'Failed to download updated files',
        status: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  // Get severity color
  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return 'red';
      case 'high': return 'orange';
      case 'medium': return 'yellow';
      case 'low': return 'green';
      default: return 'gray';
    }
  };

  // Render login screen
  if (!token) {
    return (
      <ChakraProvider>
        <Box minHeight="100vh" bg="gray.50" display="flex" alignItems="center" justifyContent="center">
          <Card maxWidth="md" width="full" mx={4}>
            <CardHeader>
              <Heading size="lg" textAlign="center" color="blue.600">
                Infotainment Accessibility Analyzer
              </Heading>
            </CardHeader>
            <CardBody>
              <VStack spacing={6}>
                <Text textAlign="center" color="gray.600">
                  Comprehensive accessibility analysis for automotive infotainment systems with smart file filtering
                </Text>

                <Button
                  colorScheme="blue"
                  size="lg"
                  width="full"
                  onClick={() => {
                    setIsRegistering(false);
                    onLoginOpen();
                  }}
                >
                  Sign In
                </Button>

                <Button
                  variant="outline"
                  size="lg"
                  width="full"
                  onClick={() => {
                    setIsRegistering(true);
                    onLoginOpen();
                  }}
                >
                  Create Account
                </Button>
              </VStack>
            </CardBody>
          </Card>

          <Modal isOpen={isLoginOpen} onClose={onLoginClose}>
            <ModalOverlay />
            <ModalContent>
              <form onSubmit={handleAuth}>
                <ModalHeader>
                  {isRegistering ? 'Create Account' : 'Sign In'}
                </ModalHeader>
                <ModalCloseButton />
                <ModalBody>
                  <VStack spacing={4}>
                    <FormControl isRequired>
                      <FormLabel>Email</FormLabel>
                      <Input name="email" type="email" placeholder="Enter your email" />
                    </FormControl>
                    <FormControl isRequired>
                      <FormLabel>Password</FormLabel>
                      <Input name="password" type="password" placeholder="Enter your password" />
                    </FormControl>
                  </VStack>
                </ModalBody>
                <ModalFooter>
                  <Button
                    type="submit"
                    colorScheme="blue"
                    mr={3}
                    isLoading={loading}
                    loadingText={isRegistering ? 'Creating...' : 'Signing in...'}
                  >
                    {isRegistering ? 'Create Account' : 'Sign In'}
                  </Button>
                  <Button variant="ghost" onClick={onLoginClose}>
                    Cancel
                  </Button>
                </ModalFooter>
              </form>
            </ModalContent>
          </Modal>
        </Box>
      </ChakraProvider>
    );
  }

  // Main application
  return (
    <ChakraProvider>
      <Box minHeight="100vh" bg="gray.50">
        {/* Header */}
        <Box bg="white" shadow="sm" px={6} py={4}>
          <Flex alignItems="center">
            <Heading size="md" color="blue.600">
              Infotainment Accessibility Analyzer
            </Heading>
            <Spacer />
            <HStack spacing={4}>
              <ConnectionStatus isLoading={!dataLoaded} hasError={connectionError} />
              {hasUnsavedChanges && (
                <Badge colorScheme="orange" variant="solid">
                  {appliedFixes.size} fixes applied
                </Badge>
              )}
              <Text fontSize="sm" color="gray.600">
                {user?.email}
              </Text>
              <Button size="sm" variant="outline" onClick={logout}>
                Sign Out
              </Button>
            </HStack>
          </Flex>
        </Box>

        <Box maxWidth="1200px" mx="auto" p={6}>
          <Tabs>
            <TabList>
              <Tab>Upload & Analyze</Tab>
              <Tab>Results ({issues.length})</Tab>
              <Tab>Insights</Tab>
              <Tab>Previous Analyses</Tab>
            </TabList>

            <TabPanels>
              {/* Upload & Analyze Tab */}
              <TabPanel>
                <VStack spacing={6} align="stretch">
                  {/* Connection Status Alert */}
                  {connectionError && (
                    <Alert status="warning" borderRadius="md">
                      <AlertIcon />
                      <VStack align="start" spacing={1} flex="1">
                        <Text fontWeight="bold">Connection Issue Detected</Text>
                        <Text fontSize="sm">
                          Using cached AI models and standards. Some features may be limited until connection is restored.
                        </Text>
                      </VStack>
                    </Alert>
                  )}

                  {/* File Upload */}
                  <Card>
                    <CardHeader>
                      <Heading size="md">Upload Infotainment Files</Heading>
                    </CardHeader>
                    <CardBody>
                      <VStack spacing={4}>
                        <Input
                          type="file"
                          multiple
                          accept=".html,.htm,.js,.jsx,.ts,.tsx,.css,.qml,.ui,.xml,.cpp,.c,.h,.hpp,.swift,.kt,.java,.json,.yaml,.yml,.zip"
                          onChange={handleFileUpload}
                          disabled={loading}
                        />

                        {/* Upload Progress */}
                        {uploadProgress && (
                          <Alert status="info">
                            <AlertIcon />
                            <VStack align="start" spacing={1} flex="1">
                              <Text fontWeight="bold">{uploadProgress.message}</Text>
                              <Text fontSize="sm">
                                Processing {uploadProgress.totalFiles} files ({uploadProgress.totalSizeMB}MB)
                              </Text>
                              <Progress size="sm" isIndeterminate width="full" />
                            </VStack>
                          </Alert>
                        )}

                        {files.length > 0 && (
                          <Box>
                            <Text fontWeight="bold" mb={2}>Selected Files:</Text>
                            <Wrap>
                              {files.map((file, index) => (
                                <WrapItem key={index}>
                                  <Tag size="sm" colorScheme="blue">
                                    <TagLabel>{file.name}</TagLabel>
                                  </Tag>
                                </WrapItem>
                              ))}
                            </Wrap>
                          </Box>
                        )}

                        {currentAnalysis && (
                          <Alert status="success">
                            <AlertIcon />
                            <VStack align="start" spacing={1}>
                              <AlertTitle>Files processed successfully!</AlertTitle>
                              <AlertDescription>
                                <VStack align="start" spacing={1}>
                                  <Text>
                                    {currentAnalysis.infotainment_files} infotainment files ready for analysis
                                  </Text>
                                  {currentAnalysis.skipped_files > 0 && (
                                    <Text fontSize="sm" color="gray.600">
                                      Skipped {currentAnalysis.skipped_files} irrelevant files (node_modules, build files, etc.)
                                    </Text>
                                  )}
                                </VStack>
                              </AlertDescription>
                            </VStack>
                          </Alert>
                        )}

                        {/* Filtering Statistics */}
                        {filteringStats && (
                          <Alert status="info">
                            <InfoIcon />
                            <VStack align="start" spacing={1} flex="1">
                              <Text fontWeight="bold">Smart File Filtering Applied:</Text>
                              <SimpleGrid columns={2} spacing={2} fontSize="sm">
                                <Text>• Excluded directories: {filteringStats.excluded_directories}</Text>
                                <Text>• Excluded extensions: {filteringStats.excluded_extensions}</Text>
                                <Text>• Files too large: {filteringStats.too_large}</Text>
                                <Text>• Not relevant: {filteringStats.not_relevant}</Text>
                              </SimpleGrid>
                            </VStack>
                          </Alert>
                        )}
                      </VStack>
                    </CardBody>
                  </Card>

                  {/* Configuration */}
                  <SimpleGrid columns={[1, 2]} spacing={6}>
                    {/* Model Selection */}
                    <Card>
                      <CardHeader>
                        <Heading size="sm">Select AI Models</Heading>
                      </CardHeader>
                      <CardBody>
                        {modelsLoading ? (
                          <VStack spacing={3}>
                            <HStack>
                              <Spinner size="sm" />
                              <Text fontSize="sm" color="gray.500">Loading AI models...</Text>
                            </HStack>
                            <Stack spacing={3} width="full">
                              <LoadingSkeleton type="checkbox" />
                              <LoadingSkeleton type="checkbox" />
                              <LoadingSkeleton type="checkbox" />
                              <LoadingSkeleton type="checkbox" />
                            </Stack>
                          </VStack>
                        ) : (
                          <CheckboxGroup
                            value={selectedModels}
                            onChange={setSelectedModels}
                          >
                            <Stack>
                              {availableModels.map(model => (
                                <Checkbox key={model.id} value={model.id}>
                                  <VStack align="start" spacing={1}>
                                    <Text fontWeight="bold">{model.name}</Text>
                                    <Text fontSize="sm" color="gray.600">
                                      {model.description}
                                    </Text>
                                  </VStack>
                                </Checkbox>
                              ))}
                            </Stack>
                          </CheckboxGroup>
                        )}
                      </CardBody>
                    </Card>

                    {/* Standards Selection */}
                    <Card>
                      <CardHeader>
                        <Heading size="sm">Accessibility Standards</Heading>
                      </CardHeader>
                      <CardBody>
                        {standardsLoading ? (
                          <VStack spacing={3}>
                            <HStack>
                              <Spinner size="sm" />
                              <Text fontSize="sm" color="gray.500">Loading standards...</Text>
                            </HStack>
                            <Stack spacing={3} width="full">
                              <LoadingSkeleton type="checkbox" />
                              <LoadingSkeleton type="checkbox" />
                              <LoadingSkeleton type="checkbox" />
                              <LoadingSkeleton type="checkbox" />
                              <LoadingSkeleton type="checkbox" />
                            </Stack>
                          </VStack>
                        ) : (
                          <CheckboxGroup
                            value={selectedStandards}
                            onChange={setSelectedStandards}
                          >
                            <Stack>
                              {availableStandards.map(standard => (
                                <Checkbox key={standard.id} value={standard.id}>
                                  <VStack align="start" spacing={1}>
                                    <Text fontWeight="bold">{standard.name}</Text>
                                    <Text fontSize="sm" color="gray.600">
                                      {standard.description}
                                    </Text>
                                  </VStack>
                                </Checkbox>
                              ))}
                            </Stack>
                          </CheckboxGroup>
                        )}
                      </CardBody>
                    </Card>
                  </SimpleGrid>

                  {/* Start Analysis */}
                  <Button
                    colorScheme="blue"
                    size="lg"
                    onClick={startAnalysis}
                    isLoading={loading}
                    loadingText="Analyzing..."
                    isDisabled={!currentAnalysis || selectedModels.length === 0 || !dataLoaded}
                  >
                    Start Accessibility Analysis
                  </Button>

                  {/* Analysis Status */}
                  {analysisStatus && (
                    <Box>
                      {analysisStatus === 'analyzing' && (
                        <Box>
                          <Progress isIndeterminate colorScheme="blue" mb={2} />
                          <VStack spacing={2}>
                            <Text textAlign="center">
                              Analyzing {currentAnalysis?.infotainment_files} infotainment files with {selectedModels.length} AI models...
                            </Text>
                            <Text fontSize="sm" color="gray.600" textAlign="center">
                              This may take several minutes for comprehensive analysis. Files are intelligently prioritized for faster processing.
                            </Text>
                            <HStack>
                              <Spinner size="sm" />
                              <Text fontSize="sm">Processing in background...</Text>
                            </HStack>
                          </VStack>
                        </Box>
                      )}
                    </Box>
                  )}
                </VStack>
              </TabPanel>

              {/* Results Tab */}
              <TabPanel>
                {issues.length > 0 ? (
                  <VStack spacing={6} align="stretch">
                    {/* Summary Stats */}
                    <SimpleGrid columns={[2, 4]} spacing={4}>
                      <Stat>
                        <StatLabel>Total Issues</StatLabel>
                        <StatNumber>{issues.length}</StatNumber>
                      </Stat>
                      <Stat>
                        <StatLabel>Safety Critical</StatLabel>
                        <StatNumber color="red.500">
                          {issues.filter(i => i.safety_critical).length}
                        </StatNumber>
                      </Stat>
                      <Stat>
                        <StatLabel>High Severity</StatLabel>
                        <StatNumber color="orange.500">
                          {issues.filter(i => i.severity === 'high' || i.severity === 'critical').length}
                        </StatNumber>
                      </Stat>
                      <Stat>
                        <StatLabel>Fixes Applied</StatLabel>
                        <StatNumber color="green.500">
                          {appliedFixes.size}
                        </StatNumber>
                      </Stat>
                    </SimpleGrid>

                    {/* Action Buttons */}
                    <HStack>
                      {hasUnsavedChanges && (
                        <Button
                          leftIcon={<DownloadIcon />}
                          colorScheme="green"
                          onClick={downloadUpdatedFiles}
                          isLoading={loading}
                          loadingText="Preparing..."
                        >
                          Download Updated Files ({appliedFixes.size} fixes)
                        </Button>
                      )}
                    </HStack>

                    {/* Issues List */}
                    <VStack spacing={4} align="stretch">
                      {issues.map((issue) => (
                        <Card key={issue.id} variant={issue.safety_critical ? 'outline' : 'filled'}>
                          <CardBody>
                            <VStack align="stretch" spacing={3}>
                              {/* Issue Header */}
                              <Flex align="center" wrap="wrap" gap={2}>
                                <Badge colorScheme={getSeverityColor(issue.severity)}>
                                  {issue.severity?.toUpperCase()}
                                </Badge>

                                {issue.safety_critical && (
                                  <Badge colorScheme="red" variant="solid">
                                    <Icon as={WarningIcon} mr={1} />
                                    SAFETY CRITICAL
                                  </Badge>
                                )}

                                <Badge variant="outline">
                                  {issue.model}
                                </Badge>

                                <Spacer />

                                <Text fontSize="sm" color="gray.600">
                                  {issue.file}:{issue.line}
                                </Text>
                              </Flex>

                              {/* Issue Content */}
                              <Box>
                                <Heading size="sm" mb={2}>{issue.type}</Heading>
                                <Text mb={3}>{issue.description}</Text>

                                {/* Code Sections */}
                                {issue.original_code && (
                                  <Accordion allowToggle>
                                    <AccordionItem>
                                      <AccordionButton>
                                        <Box flex="1" textAlign="left">
                                          View Code & Fix
                                        </Box>
                                        <AccordionIcon />
                                      </AccordionButton>
                                      <AccordionPanel>
                                        <VStack align="stretch" spacing={3}>
                                          <Box>
                                            <Text fontSize="sm" fontWeight="bold" mb={1}>Original Code:</Text>
                                            <Box bg="gray.100" p={3} borderRadius="md" overflow="auto">
                                              <Code fontSize="sm" whiteSpace="pre-wrap">
                                                {issue.original_code}
                                              </Code>
                                            </Box>
                                          </Box>

                                          {issue.suggested_fix && (
                                            <Box>
                                              <Text fontSize="sm" fontWeight="bold" mb={1}>Suggested Fix:</Text>
                                              <Box bg="green.50" p={3} borderRadius="md" overflow="auto">
                                                <Code fontSize="sm" whiteSpace="pre-wrap" color="green.800">
                                                  {issue.suggested_fix}
                                                </Code>
                                              </Box>
                                            </Box>
                                          )}
                                        </VStack>
                                      </AccordionPanel>
                                    </AccordionItem>
                                  </Accordion>
                                )}

                                {/* Actions */}
                                <Flex justify="space-between" align="center" pt={2}>
                                  <Box />
                                  <HStack>
                                    {/* New View Code & Interface button */}
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      colorScheme="purple"
                                      leftIcon={<ViewIcon />}
                                      onClick={() => openCodeModal(issue)}
                                    >
                                      View Code & Interface
                                    </Button>

                                    {issue.fix_applied ? (
                                      <>
                                        <Badge colorScheme="green" variant="solid">
                                          <Icon as={CheckIcon} mr={1} />
                                          Applied
                                        </Badge>
                                        <Button
                                          size="sm"
                                          variant="outline"
                                          colorScheme="orange"
                                          onClick={() => undoFix(issue.id)}
                                          isLoading={loading}
                                          leftIcon={<RepeatIcon />}
                                        >
                                          Undo Fix
                                        </Button>
                                      </>
                                    ) : (
                                      <Button
                                        size="sm"
                                        colorScheme="blue"
                                        onClick={() => applyFix(issue.id)}
                                        isLoading={loading}
                                        isDisabled={!issue.suggested_fix}
                                      >
                                        Apply Fix
                                      </Button>
                                    )}
                                  </HStack>
                                </Flex>
                              </Box>
                            </VStack>
                          </CardBody>
                        </Card>
                      ))}
                    </VStack>

                    {/* Bottom Download Button */}
                    {hasUnsavedChanges && (
                      <Card bg="green.50" borderColor="green.200">
                        <CardBody>
                          <Flex align="center" justify="space-between">
                            <VStack align="start" spacing={1}>
                              <Text fontWeight="bold" color="green.800">
                                {appliedFixes.size} fixes have been applied to your files
                              </Text>
                              <Text fontSize="sm" color="green.600">
                                Download the updated files to get your fixed code
                              </Text>
                            </VStack>
                            <Button
                              leftIcon={<DownloadIcon />}
                              colorScheme="green"
                              size="lg"
                              onClick={downloadUpdatedFiles}
                              isLoading={loading}
                              loadingText="Preparing ZIP..."
                            >
                              Download Updated Files
                            </Button>
                          </Flex>
                        </CardBody>
                      </Card>
                    )}
                  </VStack>
                ) : (
                  <Box textAlign="center" py={10}>
                    <Text color="gray.500">No issues found yet. Upload files and run analysis.</Text>
                  </Box>
                )}
              </TabPanel>

              {/* Insights Tab */}
              <TabPanel>
                {infotainmentInsights ? (
                  <VStack spacing={6} align="stretch">
                    <Card>
                      <CardHeader>
                        <Heading size="md" color="red.600">Safety Assessment</Heading>
                      </CardHeader>
                      <CardBody>
                        <SimpleGrid columns={[1, 3]} spacing={4}>
                          <Stat>
                            <StatLabel>Safety Critical Issues</StatLabel>
                            <StatNumber color="red.500">
                              {infotainmentInsights.safety_assessment.total_safety_critical}
                            </StatNumber>
                            <StatHelpText>Requires immediate attention</StatHelpText>
                          </Stat>
                          <Stat>
                            <StatLabel>Eyes Off Road Violations</StatLabel>
                            <StatNumber color="orange.500">
                              {infotainmentInsights.safety_assessment.eyes_off_road_violations.length}
                            </StatNumber>
                            <StatHelpText>Over 2 second rule</StatHelpText>
                          </Stat>
                          <Stat>
                            <StatLabel>Task Time Violations</StatLabel>
                            <StatNumber color="orange.500">
                              {infotainmentInsights.safety_assessment.task_time_violations.length}
                            </StatNumber>
                            <StatHelpText>Over 12 second rule</StatHelpText>
                          </Stat>
                        </SimpleGrid>
                      </CardBody>
                    </Card>

                    <Card>
                      <CardHeader>
                        <Heading size="md" color="blue.600">Interaction Analysis</Heading>
                      </CardHeader>
                      <CardBody>
                        <SimpleGrid columns={[2, 4]} spacing={4}>
                          <Stat>
                            <StatLabel>Touch Issues</StatLabel>
                            <StatNumber>{infotainmentInsights.interaction_analysis.touch_issues}</StatNumber>
                          </Stat>
                          <Stat>
                            <StatLabel>Voice Issues</StatLabel>
                            <StatNumber>{infotainmentInsights.interaction_analysis.voice_issues}</StatNumber>
                          </Stat>
                          <Stat>
                            <StatLabel>Physical Button</StatLabel>
                            <StatNumber>{infotainmentInsights.interaction_analysis.physical_button_issues}</StatNumber>
                          </Stat>
                          <Stat>
                            <StatLabel>Steering Wheel</StatLabel>
                            <StatNumber>{infotainmentInsights.interaction_analysis.steering_wheel_issues}</StatNumber>
                          </Stat>
                        </SimpleGrid>
                      </CardBody>
                    </Card>

                    <Card>
                      <CardHeader>
                        <Heading size="md" color="purple.600">Standards Compliance</Heading>
                      </CardHeader>
                      <CardBody>
                        <SimpleGrid columns={[1, 3]} spacing={4}>
                          <Box>
                            <Text fontWeight="bold" mb={2}>WCAG Violations</Text>
                            <VStack align="start" spacing={1}>
                              <HStack>
                                <Badge colorScheme="red">Level A</Badge>
                                <Text>{infotainmentInsights.standards_compliance.wcag_a_violations}</Text>
                              </HStack>
                              <HStack>
                                <Badge colorScheme="orange">Level AA</Badge>
                                <Text>{infotainmentInsights.standards_compliance.wcag_aa_violations}</Text>
                              </HStack>
                              <HStack>
                                <Badge colorScheme="yellow">Level AAA</Badge>
                                <Text>{infotainmentInsights.standards_compliance.wcag_aaa_violations}</Text>
                              </HStack>
                            </VStack>
                          </Box>
                          <Box>
                            <Text fontWeight="bold" mb={2}>Automotive Standards</Text>
                            <VStack align="start" spacing={1}>
                              <HStack>
                                <Badge colorScheme="green">ISO 15008</Badge>
                                <Text>{infotainmentInsights.standards_compliance.iso15008_issues}</Text>
                              </HStack>
                              <HStack>
                                <Badge colorScheme="orange">NHTSA</Badge>
                                <Text>{infotainmentInsights.standards_compliance.nhtsa_issues}</Text>
                              </HStack>
                            </VStack>
                          </Box>
                          <Box>
                            <Text fontWeight="bold" mb={2}>Overall Compliance</Text>
                            <CircularProgress
                              value={Math.max(0, 100 - (issues.length * 2))}
                              color="green.400"
                              size="80px"
                            >
                              <CircularProgressLabel>
                                {Math.max(0, 100 - (issues.length * 2))}%
                              </CircularProgressLabel>
                            </CircularProgress>
                          </Box>
                        </SimpleGrid>
                      </CardBody>
                    </Card>

                    {/* Recommendations */}
                    {infotainmentInsights.recommendations && infotainmentInsights.recommendations.length > 0 && (
                      <Card>
                        <CardHeader>
                          <Heading size="md" color="teal.600">Recommendations</Heading>
                        </CardHeader>
                        <CardBody>
                          <VStack align="stretch" spacing={3}>
                            {infotainmentInsights.recommendations.map((rec, index) => (
                              <Alert
                                key={index}
                                status={rec.priority === 'critical' ? 'error' : rec.priority === 'high' ? 'warning' : 'info'}
                              >
                                <AlertIcon />
                                <VStack align="start" spacing={1}>
                                  <HStack>
                                    <Badge colorScheme={rec.priority === 'critical' ? 'red' : rec.priority === 'high' ? 'orange' : 'blue'}>
                                      {rec.priority.toUpperCase()}
                                    </Badge>
                                    <Text fontWeight="bold">{rec.category}</Text>
                                  </HStack>
                                  <Text>{rec.message}</Text>
                                </VStack>
                              </Alert>
                            ))}
                          </VStack>
                        </CardBody>
                      </Card>
                    )}
                  </VStack>
                ) : (
                  <Box textAlign="center" py={10}>
                    <Text color="gray.500">No insights available yet. Complete an analysis first.</Text>
                  </Box>
                )}
              </TabPanel>

              {/* Previous Analyses Tab */}
              <TabPanel>
                {analyses.length > 0 ? (
                  <VStack spacing={4} align="stretch">
                    {analyses.map(analysis => (
                      <Card key={analysis.id} cursor="pointer">
                        <CardBody>
                          <Flex justify="space-between" align="center">
                            <VStack align="start" spacing={1}>
                              <HStack>
                                <Badge colorScheme={
                                  analysis.status === 'completed' ? 'green' :
                                  analysis.status === 'analyzing' ? 'blue' :
                                  analysis.status === 'failed' ? 'red' : 'gray'
                                }>
                                  {analysis.status}
                                </Badge>
                                <Text fontWeight="bold">
                                  {analysis.files?.length || 0} files
                                </Text>
                              </HStack>
                              <Text fontSize="sm" color="gray.600">
                                {new Date(analysis.created_at).toLocaleString()}
                              </Text>
                              {analysis.models && (
                                <Text fontSize="xs" color="gray.500">
                                  Models: {analysis.models.join(', ')}
                                </Text>
                              )}
                            </VStack>
                            <VStack spacing={2}>
                              <Button
                                size="sm"
                                colorScheme="blue"
                                onClick={async () => {
                                  try {
                                    const response = await fetch(`${API_URL}/analysis/${analysis.id}`, {
                                      headers: { 'Authorization': `Bearer ${token}` }
                                    });
                                    if (response.ok) {
                                      const data = await response.json();
                                      setCurrentAnalysis(data.analysis);
                                      setIssues(data.issues || []);
                                      setAnalysisStatus('completed');
                                      setSelectedStandards(data.analysis.selected_standards || []);

                                      // Fetch insights for this analysis
                                      fetchInfotainmentInsights(analysis.id);

                                      toast({
                                        title: `Analysis loaded: ${data.issues.length} issues found`,
                                        status: 'success'
                                      });
                                    } else {
                                      toast({ title: 'Failed to load analysis', status: 'error' });
                                    }
                                  } catch (error) {
                                    console.error('Load analysis error:', error);
                                    toast({ title: 'Failed to load analysis', status: 'error' });
                                  }
                                }}
                              >
                                Load Analysis
                              </Button>
                            </VStack>
                          </Flex>
                        </CardBody>
                      </Card>
                    ))}
                  </VStack>
                ) : (
                  <Box textAlign="center" py={10}>
                    <Text color="gray.500">No previous analyses found.</Text>
                  </Box>
                )}
              </TabPanel>
            </TabPanels>
          </Tabs>
        </Box>

        {/* Code Issue Modal */}
        <CodeIssueModal
          isOpen={isCodeModalOpen}
          onClose={onCodeModalClose}
          issue={selectedIssue}
          fileContent={selectedFileContent}
          allFileContents={currentAnalysis?.file_contents}
        />
      </Box>
    </ChakraProvider>
  );
}

export default App;