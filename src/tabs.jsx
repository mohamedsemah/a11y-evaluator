import React from 'react';
import {
  Box,
  VStack,
  HStack,
  Button,
  Input,
  Text,
  Heading,
  Alert,
  AlertIcon,
  Progress,
  Badge,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Checkbox,
  Tooltip,
  IconButton,
  SimpleGrid,
  Grid,
  GridItem,
  Card,
  CardHeader,
  CardBody,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText
} from '@chakra-ui/react';
import {
  FaUpload,
  FaPlay,
  FaDownload,
  FaStar,
  FaCheck,
  FaCode,
  FaEye,
  FaCar,
  FaExclamationTriangle,
  FaHandPaper,
  FaMicrophone,
  FaGamepad,
  FaChartLine
} from 'react-icons/fa';

import { VehicleContextCard, StandardsSelectionCard, ModelSelectionCard } from './components';
import { JumpToCodeModal } from './JumpToCodeModal';

// Helper functions
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

const formatIssueType = (type) => {
  return type.split('_').map(word =>
    word.charAt(0).toUpperCase() + word.slice(1)
  ).join(' ');
};

const getInteractionMethodIcon = (method) => {
  const icons = {
    'touch': FaHandPaper,
    'voice': FaMicrophone,
    'gesture': FaGamepad,
    'physical_button': FaGamepad,
    'steering_wheel': FaCar,
    'mixed': FaGamepad
  };
  return icons[method] || FaGamepad;
};

const getIssueTypeExplanation = (type) => {
  const explanations = {
    // Visual & Display Issues
    'inadequate_daylight_contrast': 'Text/icons not visible in bright sunlight - critical safety issue',
    'inadequate_night_contrast': 'Poor visibility in dark conditions affecting driver safety',
    'character_too_small_driving': 'Text too small for safe reading while driving - violates ISO 15008',
    'excessive_visual_complexity': 'Too much information causing cognitive overload while driving',
    'poor_glare_control': 'Reflections interfering with display visibility',
    'color_dependency_driving': 'Critical info relies only on color - inaccessible in various lighting',
    'animation_distraction': 'Moving elements cause dangerous distraction while driving',

    // Interaction & Control Issues
    'complex_gesture_while_driving': 'Multi-touch gestures unsafe for drivers - violates NHTSA guidelines',
    'inadequate_touch_targets': 'Touch areas too small for vehicle vibration/movement',
    'missing_physical_backup': 'No physical button alternative for critical touch controls',
    'steering_wheel_inaccessible': 'Functions not reachable from steering wheel controls',
    'voice_command_mismatch': 'Voice commands don\'t match visible labels - confuses users',
    'accidental_activation': 'Easy to trigger unintended actions while driving',
    'poor_haptic_feedback': 'Insufficient tactile confirmation of actions',

    // Timing & Attention Issues
    'excessive_task_time': 'Tasks take too long, causing extended distraction (>12s violates NHTSA)',
    'excessive_glance_time': 'Single glances exceed safe 2-second limit',
    'excessive_glance_count': 'Too many glances needed to complete task',
    'no_progress_indication': 'User can\'t estimate remaining task time',
    'timeout_too_short': 'Interface times out before driver can safely respond',
    'cognitive_overload': 'Too much mental processing required while driving',

    // Audio & Voice Issues
    'inadequate_voice_feedback': 'Poor or missing audio confirmation of actions',
    'speech_interference': 'Background noise interferes with voice commands',
    'missing_audio_alternatives': 'Visual-only feedback inaccessible while driving',
    'inconsistent_voice_commands': 'Voice interface behaves unpredictably',
    'no_audio_ducking': 'Media doesn\'t reduce volume for navigation/alerts',
    'poor_speech_recognition': 'Voice system frequently misunderstands commands',

    // Safety & Emergency Issues
    'blocked_critical_info': 'Safety info obscured by other interface elements',
    'emergency_function_buried': 'Emergency features not quickly accessible',
    'system_failure_unsafe': 'Interface fails unsafely or without warning',
    'driver_trap': 'Interface state prevents return to safe operation',
    'attention_capture': 'Interface demands attention at unsafe moments',

    // Traditional web issues enhanced for automotive
    'missing_alt_text': 'Images without alternative text make voice control impossible',
    'low_contrast': 'Insufficient color contrast for automotive lighting conditions',
    'missing_label': 'Form controls without proper labels break voice navigation',
    'keyboard_trap': 'Users trapped in interface - critical safety issue in vehicles',
    'aria_issue': 'ARIA attributes missing, breaking assistive technology integration',
    'focus_issue': 'Focus management problems affecting safe navigation',
    'semantic_issue': 'Improper HTML semantics confusing voice control systems'
  };
  return explanations[type] || 'Accessibility issue detected in infotainment system';
};

const API_URL = 'http://localhost:8000/api';

// Analysis Tab Component
export const AnalysisTab = ({
  files,
  fileInputRef,
  loading,
  currentAnalysis,
  analysisStatus,
  vehicleContext,
  setVehicleContext,
  selectedStandards,
  setSelectedStandards,
  availableStandards,
  selectedModels,
  setSelectedModels,
  handleFileUpload,
  startAnalysis
}) => (
  <VStack spacing={5} align="stretch">
    {/* File Upload */}
    <Card>
      <CardHeader>
        <HStack>
          <FaUpload />
          <Heading size="md">Upload Infotainment Files</Heading>
        </HStack>
      </CardHeader>
      <CardBody>
        <VStack spacing={4}>
          <Input
            type="file"
            multiple
            accept=".html,.css,.js,.jsx,.ts,.tsx,.qml,.ui,.xml,.cpp,.c,.h,.swift,.kt,.java,.json,.zip"
            onChange={handleFileUpload}
            ref={fileInputRef}
            display="none"
          />
          <Button
            leftIcon={<FaUpload />}
            onClick={() => fileInputRef.current?.click()}
            colorScheme="automotive"
            size="lg"
            width="full"
            isLoading={loading && !currentAnalysis}
            loadingText="Uploading..."
          >
            Upload Infotainment Code Files (Max 50MB each)
          </Button>

          {files.length > 0 && (
            <Box width="full">
              <Text fontWeight="bold" mb={2}>Uploaded Files:</Text>
              <SimpleGrid columns={2} spacing={2}>
                {files.map((file, idx) => (
                  <HStack key={idx}>
                    <FaCode />
                    <Text fontSize="sm">{file.name}</Text>
                    <Badge>{(file.size / 1024).toFixed(1)} KB</Badge>
                  </HStack>
                ))}
              </SimpleGrid>
            </Box>
          )}

          {analysisStatus === 'uploaded' && currentAnalysis && (
            <Alert status="success">
              <AlertIcon />
              <VStack align="start" spacing={1}>
                <Text>
                  Files uploaded successfully! {currentAnalysis.infotainment_files} infotainment files detected.
                </Text>
                <Text fontSize="sm">
                  Configure analysis settings below and start analysis.
                </Text>
              </VStack>
            </Alert>
          )}
        </VStack>
      </CardBody>
    </Card>

    {/* Vehicle Context Configuration */}
    <VehicleContextCard
      vehicleContext={vehicleContext}
      setVehicleContext={setVehicleContext}
    />

    {/* Standards Selection */}
    <StandardsSelectionCard
      selectedStandards={selectedStandards}
      setSelectedStandards={setSelectedStandards}
      availableStandards={availableStandards}
    />

    {/* LLM Model Selection */}
    <ModelSelectionCard
      selectedModels={selectedModels}
      setSelectedModels={setSelectedModels}
    />

    {/* Start Analysis Button */}
    <Button
      leftIcon={<FaPlay />}
      colorScheme="green"
      size="lg"
      onClick={startAnalysis}
      isLoading={loading && analysisStatus === 'analyzing'}
      loadingText="Analyzing infotainment accessibility..."
      isDisabled={!currentAnalysis || selectedModels.length === 0 || selectedStandards.length === 0}
    >
      Start Infotainment Analysis ({selectedModels.length} models, {selectedStandards.length} standards)
    </Button>

    {analysisStatus === 'analyzing' && (
      <Alert status="info">
        <AlertIcon />
        <VStack align="start" spacing={1}>
          <Text>
            Analyzing {currentAnalysis?.infotainment_files} infotainment files using {selectedModels.join(', ')}
          </Text>
          <Text fontSize="sm">
            Checking against: {selectedStandards.join(', ')}
          </Text>
          <Progress size="sm" isIndeterminate width="full" />
        </VStack>
      </Alert>
    )}
  </VStack>
);

// Results Tab Component
export const ResultsTab = ({
  loading,
  analysisStatus,
  issues,
  selectedStandards,
  selectedModels,
  selectedIssues,
  setSelectedIssues,
  infotainmentInsights,
  onInsightsOpen,
  applySelectedFixes,
  downloadReport,
  rateIssue,
  setCodeView,
  onDiffOpen,
  currentAnalysis
}) => {
  const [isJumpOpen, setIsJumpOpen] = useState(false);
const [jumpData, setJumpData] = useState({ file: '', content: '', line: 1 });
  if (loading && analysisStatus === 'analyzing') {
    return (
      <VStack spacing={4}>
        <Text>Analyzing infotainment accessibility with selected models...</Text>
        <Text fontSize="sm" color="gray.600">
          This may take several minutes for comprehensive automotive standards analysis
        </Text>
        <Progress size="lg" isIndeterminate width="full" />

      </VStack>
    );
  }

  if (issues.length > 0) {
    return (
      <VStack spacing={5} align="stretch">
        {/* Results Header */}
        <HStack justify="space-between">
          <VStack align="start" spacing={1}>
            <Heading size="md">
              Found {issues.length} Issues
              {issues.filter(i => i.safety_critical).length > 0 && (
                <Badge colorScheme="red" ml={2}>
                  {issues.filter(i => i.safety_critical).length} Safety Critical
                </Badge>
              )}
            </Heading>
            <Text fontSize="sm" color="gray.600">
              Analyzed against: {selectedStandards.join(', ')}
            </Text>
          </VStack>
          <HStack>
            <Button
              leftIcon={<FaChartLine />}
              onClick={onInsightsOpen}
              colorScheme="blue"
              isDisabled={!infotainmentInsights}
            >
              View Insights
            </Button>
            <Button
              leftIcon={<FaCheck />}
              onClick={applySelectedFixes}
              colorScheme="green"
              isDisabled={selectedIssues.size === 0}
            >
              Apply Selected ({selectedIssues.size})
            </Button>
            <Button
              leftIcon={<FaDownload />}
              onClick={downloadReport}
              colorScheme="automotive"
            >
              Download Report
            </Button>
          </HStack>
        </HStack>

        {/* Quick Stats */}
        <SimpleGrid columns={5} spacing={4}>
          <Stat>
            <StatLabel>
              <HStack>
                <FaExclamationTriangle color="red" />
                <Text>Safety Critical</Text>
              </HStack>
            </StatLabel>
            <StatNumber color="red.500">
              {issues.filter(i => i.safety_critical).length}
            </StatNumber>
          </Stat>
          <Stat>
            <StatLabel>WCAG A Violations</StatLabel>
            <StatNumber color="orange.500">
              {issues.filter(i => i.wcag_level === 'A').length}
            </StatNumber>
          </Stat>
          <Stat>
            <StatLabel>WCAG AA Violations</StatLabel>
            <StatNumber color="yellow.500">
              {issues.filter(i => i.wcag_level === 'AA').length}
            </StatNumber>
          </Stat>
          <Stat>
            <StatLabel>Touch Issues</StatLabel>
            <StatNumber>
              {issues.filter(i => i.interaction_method === 'touch').length}
            </StatNumber>
          </Stat>
          <Stat>
            <StatLabel>Voice Issues</StatLabel>
            <StatNumber>
              {issues.filter(i => i.interaction_method === 'voice').length}
            </StatNumber>
          </Stat>
        </SimpleGrid>

        {/* Issues Table */}
        <Box overflowX="auto">
          <Table variant="simple" size="sm">
            <Thead>
              <Tr>
                <Th>Select</Th>
                <Th>Safety</Th>
                <Th>File</Th>
                <Th>Type</Th>
                <Th>Severity</Th>
                <Th>Interaction</Th>
                <Th>Standards</Th>
                <Th>Automotive Metrics</Th>
                <Th>Model</Th>
                <Th>Rating</Th>
                <Th>Actions</Th>
              </Tr>
            </Thead>
            <Tbody>
              {issues.map((issue) => (
                <Tr key={issue.id} bg={issue.safety_critical ? 'red.50' : 'white'}>
                  <Td>
                    <Checkbox
                      isChecked={selectedIssues.has(issue.id)}
                      onChange={(e) => {
                        const newSelected = new Set(selectedIssues);
                        if (e.target.checked) {
                          newSelected.add(issue.id);
                        } else {
                          newSelected.delete(issue.id);
                        }
                        setSelectedIssues(newSelected);
                      }}
                      isDisabled={issue.fix_applied}
                    />
                  </Td>
                  <Td>
                    {issue.safety_critical && (
                      <Tooltip label="Safety Critical Issue">
                        <FaExclamationTriangle color="red" />
                      </Tooltip>
                    )}
                  </Td>
                  <Td>
                    <Text fontSize="sm" noOfLines={1}>{issue.file}</Text>
                    <Text fontSize="xs" color="gray.500">Line {issue.line}</Text>
                  </Td>
                  <Td>
                    <Tooltip
                      label={getIssueTypeExplanation(issue.type)}
                      hasArrow
                      placement="top"
                      bg="gray.700"
                      color="white"
                      p={4}
                      borderRadius="lg"
                      maxW="400px"
                      fontSize="sm"
                    >
                      <Badge cursor="help" colorScheme="blue">
                        {formatIssueType(issue.type)}
                      </Badge>
                    </Tooltip>
                  </Td>
                  <Td>
                    <Badge colorScheme={getSeverityColor(issue.severity)}>
                      {issue.severity}
                    </Badge>
                  </Td>
                  <Td>
                    <HStack>
                      {React.createElement(getInteractionMethodIcon(issue.interaction_method), { size: 16 })}
                      <Text fontSize="sm">{issue.interaction_method}</Text>
                    </HStack>
                  </Td>
                  <Td>
                    <VStack align="start" spacing={1}>
                      {issue.wcag_criteria?.slice(0, 2).map((criteria, i) => (
                        <Badge key={i} size="sm" colorScheme="blue">{criteria}</Badge>
                      ))}
                      {issue.nhtsa_criteria?.length > 0 && (
                        <Badge size="sm" colorScheme="orange">NHTSA</Badge>
                      )}
                      {issue.iso15008_criteria?.length > 0 && (
                        <Badge size="sm" colorScheme="green">ISO15008</Badge>
                      )}
                    </VStack>
                  </Td>
                  <Td>
                    {issue.automotive_metrics && (
                      <VStack align="start" spacing={0}>
                        <Text fontSize="xs">
                          Eyes: {issue.automotive_metrics.eyes_off_road_time}s
                        </Text>
                        <Text fontSize="xs">
                          Task: {issue.automotive_metrics.task_time}s
                        </Text>
                        <Text fontSize="xs">
                          Glances: {issue.automotive_metrics.glance_count}
                        </Text>
                      </VStack>
                    )}
                  </Td>
                  <Td>
                    <Text fontSize="sm">{issue.model}</Text>
                  </Td>
                  <Td>
                    <HStack>
                      {[1, 2, 3, 4, 5].map((star) => (
                        <IconButton
                          key={star}
                          icon={<FaStar />}
                          size="xs"
                          variant="ghost"
                          color={issue.user_rating >= star ? 'yellow.400' : 'gray.300'}
                          onClick={() => rateIssue(issue.id, star)}
                        />
                      ))}
                    </HStack>
                  </Td>
                  <Td>
  <VStack align="start">
    <HStack>
      <IconButton
        icon={<FaEye />}
        size="sm"
        onClick={() => {
          setCodeView({ show: true, issue });
          onDiffOpen();
        }}
        title="View code diff"
      />
      <Button
        size="sm"
        colorScheme="blue"
        variant="outline"
        onClick={() => {
          const fileContent = currentAnalysis.file_contents[issue.file];
          setJumpData({
            file: issue.file,
            content: fileContent,
            line: issue.line || 1
          });
          setIsJumpOpen(true);
        }}
      >
        Jump to Code
      </Button>
    </HStack>
    {issue.fix_applied && (
      <Badge colorScheme="green" fontSize="xs">Applied</Badge>
    )}
  </VStack>
</Td>

                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>

        {/* Model Performance Comparison */}
        <Grid templateColumns="repeat(auto-fit, minmax(250px, 1fr))" gap={4}>
          {selectedModels.map(model => {
            const modelIssues = issues.filter(i => i.model === model);
            const displayName = model === 'Deepseek-V3' ? 'DeepSeek V3' :
                               model === 'gpt-4o' ? 'GPT-4o' :
                               model === 'claude-opus-4' ? 'Claude Opus 4' : model;
            const avgRating = modelIssues.length > 0
              ? (modelIssues.filter(i => i.user_rating).reduce((sum, i) => sum + i.user_rating, 0) / modelIssues.filter(i => i.user_rating).length).toFixed(1)
              : 'N/A';
            const safetyIssues = modelIssues.filter(i => i.safety_critical).length;

            return (
              <GridItem key={model}>
                <Card>
                  <CardBody>
                    <Stat>
                      <StatLabel>{displayName}</StatLabel>
                      <StatNumber>{modelIssues.length}</StatNumber>
                      <StatHelpText>
                        issues • {safetyIssues} safety critical
                        {avgRating !== 'N/A' && ` • ${avgRating}★ avg`}
                      </StatHelpText>
                    </Stat>
                  </CardBody>
                </Card>
              </GridItem>
            );
          })}
        </Grid>
        <JumpToCodeModal
  isOpen={isJumpOpen}
  onClose={() => setIsJumpOpen(false)}
  file={jumpData.file}
  content={jumpData.content}
  line={jumpData.line}
/>

      </VStack>
    );
  }

  if (analysisStatus === 'completed') {
    return (
      <Alert status="success">
        <AlertIcon />
        <VStack align="start" spacing={2}>
          <Text fontWeight="bold">Analysis completed successfully!</Text>
          <Text>No accessibility issues were found in your infotainment code.</Text>
          <Text fontSize="sm" color="gray.600">
            This means your code meets the selected accessibility standards.
          </Text>
        </VStack>
      </Alert>
    );
  }

  if (analysisStatus === 'failed') {
    return (
      <Alert status="error">
        <AlertIcon />
        <VStack align="start" spacing={2}>
          <Text fontWeight="bold">Analysis failed</Text>
          <Text>Please try again or check your API configuration.</Text>
        </VStack>
      </Alert>
    );
  }

  return (
    <Alert status="info">
      <AlertIcon />
      <VStack align="start" spacing={2}>
        <Text fontWeight="bold">No analysis results yet</Text>
        <Text>Upload infotainment files and start analysis in the "New Analysis" tab.</Text>
      </VStack>
    </Alert>
  );
};

// History Tab Component
export const HistoryTab = ({
  analyses,
  token,
  setCurrentAnalysis,
  setIssues,
  setAnalysisStatus,
  setSelectedStandards,
  fetchInfotainmentInsights,
  toast
}) => (
  <VStack spacing={4} align="stretch">
    <Heading size="md">
      <HStack>
        <FaCar />
        <Text>Infotainment Analysis History</Text>
      </HStack>
    </Heading>
    {analyses.length > 0 ? (
      <SimpleGrid columns={1} spacing={4}>
        {analyses.map((analysis) => (
          <Card key={analysis.id}>
            <CardBody>
              <HStack justify="space-between" align="start">
                <VStack align="start" spacing={2}>
                  <HStack>
                    <Text fontWeight="bold">
                      {new Date(analysis.created_at).toLocaleDateString()}
                    </Text>
                    <Badge
                      colorScheme={
                        analysis.status === 'completed' ? 'green' :
                        analysis.status === 'failed' ? 'red' : 'yellow'
                      }
                    >
                      {analysis.status}
                    </Badge>
                    {analysis.safety_critical_issues > 0 && (
                      <Badge colorScheme="red">
                        {analysis.safety_critical_issues} Safety Critical
                      </Badge>
                    )}
                  </HStack>
                  <HStack spacing={4}>
                    <Text fontSize="sm">
                      <strong>Files:</strong> {analysis.total_files}
                    </Text>
                    <Text fontSize="sm">
                      <strong>Models:</strong> {analysis.models?.join(', ') || 'N/A'}
                    </Text>
                    <Text fontSize="sm">
                      <strong>Standards:</strong> {analysis.standards?.join(', ') || 'N/A'}
                    </Text>
                  </HStack>
                  {analysis.vehicle_context && (
                    <HStack spacing={2} flexWrap="wrap">
                      <Badge variant="outline">
                        {analysis.vehicle_context.driving_mode ? 'Driving Mode' : 'Parked Mode'}
                      </Badge>
                      <Badge variant="outline">
                        {analysis.vehicle_context.lighting_condition}
                      </Badge>
                      <Badge variant="outline">
                        {analysis.vehicle_context.speed_range} km/h
                      </Badge>
                    </HStack>
                  )}
                </VStack>
                <VStack spacing={2}>
                  <Button
                    size="sm"
                    colorScheme="automotive"
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
                  {analysis.status === 'completed' && (
                    <Button
                      size="sm"
                      variant="outline"
                      leftIcon={<FaDownload />}
                      onClick={async () => {
                        try {
                          const response = await fetch(`${API_URL}/analysis/${analysis.id}/report`, {
                            headers: { 'Authorization': `Bearer ${token}` }
                          });
                          if (response.ok) {
                            const blob = await response.blob();
                            const url = window.URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = `infotainment_report_${analysis.id}.pdf`;
                            a.click();
                            window.URL.revokeObjectURL(url);
                          }
                        } catch (error) {
                          toast({ title: 'Failed to download report', status: 'error' });
                        }
                      }}
                    >
                      Report
                    </Button>
                  )}
                </VStack>
              </HStack>
            </CardBody>
          </Card>
        ))}
      </SimpleGrid>
    ) : (
      <Alert status="info">
        <AlertIcon />
        <VStack align="start" spacing={2}>
          <Text fontWeight="bold">No previous analyses found</Text>
          <Text>Start your first infotainment accessibility analysis in the "New Analysis" tab.</Text>
        </VStack>
      </Alert>
    )}
  </VStack>
);