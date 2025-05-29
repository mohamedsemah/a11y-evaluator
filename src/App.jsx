import React, { useState, useEffect } from 'react';
import {
  ChakraProvider,
  Box,
  VStack,
  HStack,
  Text,
  Button,
  Input,
  Textarea,
  Select,
  useToast,
  Spinner,
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
  Divider,
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
  WrapItem
} from '@chakra-ui/react';
import { WarningIcon, CheckIcon, InfoIcon } from '@chakra-ui/icons';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

function App() {
  // Authentication state
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(null);
  const [isRegistering, setIsRegistering] = useState(false);

  // Modal controls
  const { isOpen: isLoginOpen, onOpen: onLoginOpen, onClose: onLoginClose } = useDisclosure();

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

  // Available options
  const [availableModels, setAvailableModels] = useState([]);
  const [availableStandards, setAvailableStandards] = useState([]);

  const toast = useToast();

  // Enhanced token validation on startup
  useEffect(() => {
    const validateToken = async () => {
      if (token) {
        try {
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
          } else if (response.ok) {
            // Token is valid, fetch initial data
            fetchAvailableModels();
            fetchAvailableStandards();
            fetchAnalyses();
          }
        } catch (error) {
          console.error('Token validation error:', error);
          toast({
            title: 'Connection error - please check your internet connection',
            status: 'error',
            duration: 5000
          });
        }
      }
    };

    validateToken();
  }, [token]);

  // Enhanced logout with cleanup
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

        // Verify token immediately and fetch initial data
        try {
          await Promise.all([
            fetchAvailableModels(),
            fetchAvailableStandards(),
            fetchAnalyses()
          ]);

          toast({
            title: isRegistering ? 'Registration successful!' : 'Login successful!',
            status: 'success'
          });
        } catch (verifyError) {
          console.error('Post-auth data fetch failed:', verifyError);
          toast({
            title: 'Login successful, but failed to load data - please refresh',
            status: 'warning'
          });
        }
      } else {
        // Handle specific error cases
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

  // Enhanced data fetching with error handling
  const fetchAvailableModels = async () => {
    try {
      const response = await fetch(`${API_URL}/models`);
      if (response.ok) {
        const data = await response.json();
        setAvailableModels(data.models || []);
      }
    } catch (error) {
      console.error('Error fetching models:', error);
    }
  };

  const fetchAvailableStandards = async () => {
    try {
      const response = await fetch(`${API_URL}/standards`);
      if (response.ok) {
        const data = await response.json();
        setAvailableStandards(data.standards || []);
      }
    } catch (error) {
      console.error('Error fetching standards:', error);
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

  // Enhanced file upload with better error handling
  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files);
    setFiles(files);

    if (files.length === 0) return;

    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    try {
      setLoading(true);
      setAnalysisStatus('uploading');

      const response = await fetch(`${API_URL}/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });

      if (response.ok) {
        const data = await response.json();
        toast({
          title: `Files uploaded successfully!`,
          description: `${data.infotainment_files} infotainment files detected out of ${data.total_files} total files`,
          status: 'success',
          duration: 5000
        });

        setCurrentAnalysis({
          id: data.analysis_id,
          files: data.files,
          infotainment_files: data.infotainment_files,
          context_type: data.context_type
        });
        setAnalysisStatus('uploaded');

        // Refresh analyses list
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
            status: 'error'
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
    }
  };

  // Enhanced analysis function
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
          description: `Analyzing with ${selectedModels.length} models using ${selectedStandards.length} standards`,
          status: 'info',
          duration: 5000
        });

        // Poll for results
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

            // Fetch infotainment-specific insights
            fetchInfotainmentInsights(analysisId);

            toast({
              title: 'Analysis completed!',
              description: `Found ${data.issues?.length || 0} issues`,
              status: 'success'
            });

            // Refresh analyses list
            fetchAnalyses();
          } else if (data.analysis.status === 'failed') {
            setAnalysisStatus('failed');
            toast({
              title: 'Analysis failed',
              description: data.analysis.error_message || 'Unknown error',
              status: 'error'
            });
          } else {
            // Still analyzing, poll again
            setTimeout(poll, 3000);
          }
        }
      } catch (error) {
        console.error('Polling error:', error);
        setTimeout(poll, 5000); // Retry after longer delay
      }
    };

    poll();
  };

  // Fetch infotainment insights
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

  // Load previous analysis
  const loadAnalysis = async (analysisId) => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/analysis/${analysisId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.status === 401) {
        logout();
        return;
      }

      if (response.ok) {
        const data = await response.json();
        setCurrentAnalysis({
          id: analysisId,
          files: data.analysis.file_names || [],
          context_type: data.analysis.context_type
        });
        setIssues(data.issues || []);
        setAnalysisStatus(data.analysis.status);
        setSelectedModels(data.analysis.models_used || []);
        setSelectedStandards(data.analysis.standards_applied || []);

        // Fetch insights if analysis is completed
        if (data.analysis.status === 'completed') {
          fetchInfotainmentInsights(analysisId);
        }

        toast({
          title: 'Analysis loaded',
          description: `Loaded analysis with ${data.issues?.length || 0} issues`,
          status: 'info'
        });
      }
    } catch (error) {
      console.error('Error loading analysis:', error);
      toast({ title: 'Error loading analysis', status: 'error' });
    } finally {
      setLoading(false);
    }
  };

  // Rate issue
  const rateIssue = async (issueId, rating) => {
    try {
      const response = await fetch(`${API_URL}/issue/${issueId}/rate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ rating })
      });

      if (response.ok) {
        // Update local state
        setIssues(issues.map(issue =>
          issue.id === issueId ? { ...issue, user_rating: rating } : issue
        ));

        toast({ title: 'Rating saved', status: 'success', duration: 2000 });
      }
    } catch (error) {
      console.error('Error rating issue:', error);
    }
  };

  // Apply fix
  const applyFix = async (issueId) => {
    try {
      const response = await fetch(`${API_URL}/issue/${issueId}/apply`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        setIssues(issues.map(issue =>
          issue.id === issueId ? { ...issue, fix_applied: true } : issue
        ));

        toast({ title: 'Fix applied', status: 'success', duration: 2000 });
      }
    } catch (error) {
      console.error('Error applying fix:', error);
    }
  };

  // Generate report
  const generateReport = async () => {
    if (!currentAnalysis) return;

    try {
      const response = await fetch(`${API_URL}/analysis/${currentAnalysis.id}/report`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `infotainment_accessibility_report_${currentAnalysis.id}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        toast({ title: 'Report generated successfully', status: 'success' });
      }
    } catch (error) {
      console.error('Error generating report:', error);
      toast({ title: 'Error generating report', status: 'error' });
    }
  };

  // Render issue severity badge
  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return 'red';
      case 'high': return 'orange';
      case 'medium': return 'yellow';
      case 'low': return 'green';
      default: return 'gray';
    }
  };

  // Render main application
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
                  Comprehensive accessibility analysis for automotive infotainment systems
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

          {/* Auth Modal */}
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
                            <AlertTitle>Files uploaded!</AlertTitle>
                            <AlertDescription>
                              {currentAnalysis.infotainment_files} infotainment files ready for analysis
                            </AlertDescription>
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
                      </CardBody>
                    </Card>

                    {/* Standards Selection */}
                    <Card>
                      <CardHeader>
                        <Heading size="sm">Accessibility Standards</Heading>
                      </CardHeader>
                      <CardBody>
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
                    isDisabled={!currentAnalysis || selectedModels.length === 0}
                  >
                    Start Accessibility Analysis
                  </Button>

                  {/* Analysis Status */}
                  {analysisStatus && (
                    <Box>
                      {analysisStatus === 'analyzing' && (
                        <Box>
                          <Progress isIndeterminate colorScheme="blue" mb={2} />
                          <Text textAlign="center">
                            Analyzing {currentAnalysis?.infotainment_files} infotainment files with {selectedModels.length} AI models...
                          </Text>
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
                        <StatLabel>Fixed</StatLabel>
                        <StatNumber color="green.500">
                          {issues.filter(i => i.fix_applied).length}
                        </StatNumber>
                      </Stat>
                    </SimpleGrid>

                    {/* Action Buttons */}
                    <HStack>
                      <Button onClick={generateReport} variant="outline">
                        Generate Report
                      </Button>
                    </HStack>

                    {/* Issues List */}
                    <VStack spacing={4} align="stretch">
                      {issues.map((issue, index) => (
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

                                {/* Standards Information */}
                                {(issue.wcag_criteria?.length > 0 || issue.iso15008_criteria?.length > 0 || issue.nhtsa_criteria?.length > 0 || issue.sae_criteria?.length > 0 || issue.gtr8_criteria?.length > 0) && (
                                  <Box mb={3}>
                                    <Text fontSize="sm" fontWeight="bold" mb={1}>Standards Violated:</Text>
                                    <Wrap>
                                      {issue.wcag_criteria && issue.wcag_criteria.length > 0 && (
                                        <WrapItem>
                                          <Tag size="sm" colorScheme="blue">
                                            WCAG {issue.wcag_level} - {issue.wcag_principle}
                                          </Tag>
                                        </WrapItem>
                                      )}
                                      {issue.iso15008_criteria && issue.iso15008_criteria.length > 0 && (
                                        <WrapItem>
                                          <Tag size="sm" colorScheme="green">
                                            ISO 15008
                                          </Tag>
                                        </WrapItem>
                                      )}
                                      {issue.nhtsa_criteria && issue.nhtsa_criteria.length > 0 && (
                                        <WrapItem>
                                          <Tag size="sm" colorScheme="red">
                                            NHTSA
                                          </Tag>
                                        </WrapItem>
                                      )}
                                      {issue.sae_criteria && issue.sae_criteria.length > 0 && (
                                        <WrapItem>
                                          <Tag size="sm" colorScheme="orange">
                                            SAE
                                          </Tag>
                                        </WrapItem>
                                      )}
                                      {issue.gtr8_criteria && issue.gtr8_criteria.length > 0 && (
                                        <WrapItem>
                                          <Tag size="sm" colorScheme="purple">
                                            GTR8
                                          </Tag>
                                        </WrapItem>
                                      )}
                                    </Wrap>
                                  </Box>
                                )}

                                {/* Automotive Metrics */}
                                {issue.automotive_metrics && (
                                  <Box mb={3}>
                                    <Text fontSize="sm" fontWeight="bold" mb={1}>Automotive Metrics:</Text>
                                    <SimpleGrid columns={[1, 3]} spacing={2}>
                                      {issue.automotive_metrics.eyes_off_road_time > 0 && (
                                        <Text fontSize="sm">
                                          Eyes off road: {issue.automotive_metrics.eyes_off_road_time}s
                                          {issue.automotive_metrics.eyes_off_road_time > 2.0 && (
                                            <Badge ml={1} colorScheme="red" size="sm">VIOLATION</Badge>
                                          )}
                                        </Text>
                                      )}
                                      {issue.automotive_metrics.task_time > 0 && (
                                        <Text fontSize="sm">
                                          Task time: {issue.automotive_metrics.task_time}s
                                          {issue.automotive_metrics.task_time > 12.0 && (
                                            <Badge ml={1} colorScheme="red" size="sm">VIOLATION</Badge>
                                          )}
                                        </Text>
                                      )}
                                      {issue.automotive_metrics.glance_count > 0 && (
                                        <Text fontSize="sm">
                                          Glances: {issue.automotive_metrics.glance_count}
                                        </Text>
                                      )}
                                    </SimpleGrid>
                                  </Box>
                                )}

                                {/* Interaction Method */}
                                {issue.interaction_method && (
                                  <Text fontSize="sm" color="gray.600" mb={3}>
                                    Interaction method: {issue.interaction_method}
                                  </Text>
                                )}
                              </Box>

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
                                            <Text fontSize="sm" fontFamily="mono">
                                              {issue.original_code}
                                            </Text>
                                          </Box>
                                        </Box>

                                        {issue.suggested_fix && (
                                          <Box>
                                            <Text fontSize="sm" fontWeight="bold" mb={1}>Suggested Fix:</Text>
                                            <Box bg="green.50" p={3} borderRadius="md" overflow="auto">
                                              <Text fontSize="sm" fontFamily="mono">
                                                {issue.suggested_fix}
                                              </Text>
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
                                <HStack>
                                  <Text fontSize="sm">Rate this fix:</Text>
                                  {[1, 2, 3, 4, 5].map(rating => (
                                    <Button
                                      key={rating}
                                      size="xs"
                                      variant={issue.user_rating === rating ? "solid" : "outline"}
                                      colorScheme="yellow"
                                      onClick={() => rateIssue(issue.id, rating)}
                                    >
                                      {rating}
                                    </Button>
                                  ))}
                                </HStack>

                                <Button
                                  size="sm"
                                  colorScheme={issue.fix_applied ? "green" : "blue"}
                                  variant={issue.fix_applied ? "solid" : "outline"}
                                  onClick={() => applyFix(issue.id)}
                                  isDisabled={issue.fix_applied}
                                  leftIcon={issue.fix_applied ? <CheckIcon /> : undefined}
                                >
                                  {issue.fix_applied ? "Applied" : "Apply Fix"}
                                </Button>
                              </Flex>
                            </VStack>
                          </CardBody>
                        </Card>
                      ))}
                    </VStack>
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
                    {/* Safety Assessment */}
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

                        {infotainmentInsights.safety_assessment.eyes_off_road_violations.length > 0 && (
                          <Box mt={4}>
                            <Text fontWeight="bold" mb={2}>Eyes Off Road Violations:</Text>
                            {infotainmentInsights.safety_assessment.eyes_off_road_violations.map((violation, index) => (
                              <Alert key={index} status="warning" mb={2}>
                                <AlertIcon />
                                <AlertDescription>
                                  {violation.file}: {violation.time}s (Limit: 2.0s)
                                </AlertDescription>
                              </Alert>
                            ))}
                          </Box>
                        )}
                      </CardBody>
                    </Card>

                    {/* Interaction Analysis */}
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
                            <StatLabel>Button Issues</StatLabel>
                            <StatNumber>{infotainmentInsights.interaction_analysis.physical_button_issues}</StatNumber>
                          </Stat>
                          <Stat>
                            <StatLabel>Steering Wheel Issues</StatLabel>
                            <StatNumber>{infotainmentInsights.interaction_analysis.steering_wheel_issues}</StatNumber>
                          </Stat>
                        </SimpleGrid>
                      </CardBody>
                    </Card>

                    {/* Standards Compliance */}
                    <Card>
                      <CardHeader>
                        <Heading size="md" color="green.600">Standards Compliance</Heading>
                      </CardHeader>
                      <CardBody>
                        <SimpleGrid columns={[1, 2]} spacing={6}>
                          <Box>
                            <Text fontWeight="bold" mb={2}>WCAG Violations</Text>
                            <VStack align="stretch" spacing={2}>
                              <Flex justify="space-between">
                                <Text>Level A:</Text>
                                <Badge colorScheme="red">
                                  {infotainmentInsights.standards_compliance.wcag_a_violations}
                                </Badge>
                              </Flex>
                              <Flex justify="space-between">
                                <Text>Level AA:</Text>
                                <Badge colorScheme="orange">
                                  {infotainmentInsights.standards_compliance.wcag_aa_violations}
                                </Badge>
                              </Flex>
                              <Flex justify="space-between">
                                <Text>Level AAA:</Text>
                                <Badge colorScheme="yellow">
                                  {infotainmentInsights.standards_compliance.wcag_aaa_violations}
                                </Badge>
                              </Flex>
                            </VStack>
                          </Box>

                          <Box>
                            <Text fontWeight="bold" mb={2}>Automotive Standards</Text>
                            <VStack align="stretch" spacing={2}>
                              <Flex justify="space-between">
                                <Text>ISO 15008:</Text>
                                <Badge colorScheme="blue">
                                  {infotainmentInsights.standards_compliance.iso15008_issues}
                                </Badge>
                              </Flex>
                              <Flex justify="space-between">
                                <Text>NHTSA:</Text>
                                <Badge colorScheme="red">
                                  {infotainmentInsights.standards_compliance.nhtsa_issues}
                                </Badge>
                              </Flex>
                            </VStack>
                          </Box>
                        </SimpleGrid>
                      </CardBody>
                    </Card>

                    {/* Recommendations */}
                    {infotainmentInsights.recommendations.length > 0 && (
                      <Card>
                        <CardHeader>
                          <Heading size="md" color="purple.600">Recommendations</Heading>
                        </CardHeader>
                        <CardBody>
                          <VStack align="stretch" spacing={3}>
                            {infotainmentInsights.recommendations.map((rec, index) => (
                              <Alert
                                key={index}
                                status={rec.priority === 'critical' ? 'error' :
                                       rec.priority === 'high' ? 'warning' : 'info'}
                              >
                                <AlertIcon />
                                <Box>
                                  <AlertTitle>
                                    {rec.category.toUpperCase()} - {rec.priority.toUpperCase()} Priority
                                  </AlertTitle>
                                  <AlertDescription>{rec.message}</AlertDescription>
                                </Box>
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
                      <Card key={analysis.id} cursor="pointer" onClick={() => loadAnalysis(analysis.id)}>
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
                                <Text fontSize="sm" color="gray.500">
                                  Models: {analysis.models.join(', ')}
                                </Text>
                              )}
                            </VStack>

                            <VStack align="end" spacing={1}>
                              <Text fontSize="sm">
                                {analysis.context_type || 'infotainment'}
                              </Text>
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
      </Box>
    </ChakraProvider>
  );
}

export default App;