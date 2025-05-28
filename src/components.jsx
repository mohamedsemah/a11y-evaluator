import React, { useState } from 'react';
import {
  Box,
  VStack,
  HStack,
  Button,
  Input,
  FormControl,
  FormLabel,
  Text,
  Heading,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Badge,
  Alert,
  AlertIcon,
  Card,
  CardHeader,
  CardBody,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatGroup,
  Stack,
  Switch,
  Select,
  Checkbox,
  CheckboxGroup,
  SimpleGrid,
  CircularProgress,
  CircularProgressLabel
} from '@chakra-ui/react';
import { DiffEditor } from '@monaco-editor/react';
import {
  FaCar,
  FaRoad,
  FaSun,
  FaTachometerAlt,
  FaShieldAlt,
  FaHandPaper,
  FaMicrophone,
  FaGamepad,
  FaCode,
  FaExclamationTriangle,
  FaChartLine,
  FaLightbulb
} from 'react-icons/fa';

// Helper functions
const getStandardBadgeColor = (standard) => {
  const colors = {
    'WCAG': 'blue',
    'WCAG 2.2': 'blue',
    'ISO15008': 'green',
    'NHTSA': 'orange',
    'SAE_J2364': 'teal',
    'SAE_J2365': 'teal',
    'GTR8': 'red'
  };
  return colors[standard] || 'gray';
};

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

// Login Modal Component
export const LoginModal = ({ isOpen, onClose, login, register }) => {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (isRegister) {
      register(email, password);
    } else {
      login(email, password);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>
          <HStack>
            <FaCar />
            <Text>{isRegister ? 'Register' : 'Login'} - Infotainment Accessibility Analyzer</Text>
          </HStack>
        </ModalHeader>
        <ModalCloseButton />
        <form onSubmit={handleSubmit}>
          <ModalBody>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel>Email</FormLabel>
                <Input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </FormControl>
              <FormControl isRequired>
                <FormLabel>Password</FormLabel>
                <Input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </FormControl>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button type="submit" colorScheme="automotive" mr={3}>
              {isRegister ? 'Register' : 'Login'}
            </Button>
            <Button variant="ghost" onClick={() => setIsRegister(!isRegister)}>
              {isRegister ? 'Switch to Login' : 'Switch to Register'}
            </Button>
          </ModalFooter>
        </form>
      </ModalContent>
    </Modal>
  );
};

// Vehicle Context Configuration Component
export const VehicleContextCard = ({ vehicleContext, setVehicleContext }) => (
  <Card>
    <CardHeader>
      <HStack>
        <FaCar />
        <Heading size="md">Vehicle Context Configuration</Heading>
      </HStack>
    </CardHeader>
    <CardBody>
      <SimpleGrid columns={2} spacing={4}>
        <FormControl>
          <FormLabel>
            <HStack>
              <FaRoad />
              <Text>Driving Mode</Text>
            </HStack>
          </FormLabel>
          <Switch
            isChecked={vehicleContext.driving_mode}
            onChange={(e) => setVehicleContext({
              ...vehicleContext,
              driving_mode: e.target.checked
            })}
          />
          <Text fontSize="sm" color="gray.600">
            {vehicleContext.driving_mode ? 'Vehicle in motion' : 'Vehicle parked'}
          </Text>
        </FormControl>

        <FormControl>
          <FormLabel>
            <HStack>
              <FaSun />
              <Text>Lighting Condition</Text>
            </HStack>
          </FormLabel>
          <Select
            value={vehicleContext.lighting_condition}
            onChange={(e) => setVehicleContext({
              ...vehicleContext,
              lighting_condition: e.target.value
            })}
          >
            <option value="daylight">Daylight</option>
            <option value="night">Night</option>
            <option value="twilight">Twilight</option>
            <option value="variable">Variable</option>
          </Select>
        </FormControl>

        <FormControl>
          <FormLabel>
            <HStack>
              <FaTachometerAlt />
              <Text>Speed Range (km/h)</Text>
            </HStack>
          </FormLabel>
          <Select
            value={vehicleContext.speed_range}
            onChange={(e) => setVehicleContext({
              ...vehicleContext,
              speed_range: e.target.value
            })}
          >
            <option value="0">Stationary</option>
            <option value="1-30">City (1-30)</option>
            <option value="31-60">Suburban (31-60)</option>
            <option value="61+">Highway (61+)</option>
            <option value="0-120">Mixed (0-120)</option>
          </Select>
        </FormControl>

        <FormControl>
          <FormLabel>User Experience Level</FormLabel>
          <Select
            value={vehicleContext.user_experience_level}
            onChange={(e) => setVehicleContext({
              ...vehicleContext,
              user_experience_level: e.target.value
            })}
          >
            <option value="novice">Novice Driver</option>
            <option value="experienced">Experienced Driver</option>
          </Select>
        </FormControl>
      </SimpleGrid>

      <Box mt={4}>
        <FormLabel>Interaction Methods</FormLabel>
        <CheckboxGroup
          value={vehicleContext.interaction_methods}
          onChange={(methods) => setVehicleContext({
            ...vehicleContext,
            interaction_methods: methods
          })}
        >
          <Stack direction="row" wrap="wrap">
            <Checkbox value="touch">
              <HStack>
                <FaHandPaper />
                <Text>Touch</Text>
              </HStack>
            </Checkbox>
            <Checkbox value="voice">
              <HStack>
                <FaMicrophone />
                <Text>Voice</Text>
              </HStack>
            </Checkbox>
            <Checkbox value="physical_button">
              <HStack>
                <FaGamepad />
                <Text>Physical Buttons</Text>
              </HStack>
            </Checkbox>
            <Checkbox value="steering_wheel">
              <HStack>
                <FaCar />
                <Text>Steering Wheel</Text>
              </HStack>
            </Checkbox>
          </Stack>
        </CheckboxGroup>
      </Box>
    </CardBody>
  </Card>
);

// Standards Selection Component
export const StandardsSelectionCard = ({ selectedStandards, setSelectedStandards, availableStandards }) => (
  <Card>
    <CardHeader>
      <HStack>
        <FaShieldAlt />
        <Heading size="md">Accessibility Standards</Heading>
      </HStack>
    </CardHeader>
    <CardBody>
      <CheckboxGroup
        value={selectedStandards}
        onChange={setSelectedStandards}
      >
        <Stack spacing={3}>
          {availableStandards.map((standard) => (
            <Checkbox key={standard.name} value={standard.name}>
              <VStack align="start" spacing={1}>
                <HStack>
                  <Badge colorScheme={getStandardBadgeColor(standard.name)}>
                    {standard.name}
                  </Badge>
                  <Text fontWeight="bold" fontSize="sm">
                    {standard.full_name}
                  </Text>
                </HStack>
                <Text fontSize="xs" color="gray.600">
                  {standard.description}
                </Text>
                <Text fontSize="xs" color="blue.600">
                  Contexts: {standard.applicable_contexts?.join(', ')}
                </Text>
              </VStack>
            </Checkbox>
          ))}
        </Stack>
      </CheckboxGroup>
      <Alert status="info" mt={4}>
        <AlertIcon />
        <Text fontSize="sm">
          Select multiple standards for comprehensive infotainment accessibility analysis.
          WCAG + automotive standards recommended.
        </Text>
      </Alert>
    </CardBody>
  </Card>
);

// Model Selection Component
export const ModelSelectionCard = ({ selectedModels, setSelectedModels }) => (
  <Card>
    <CardHeader>
      <HStack>
        <FaCode />
        <Heading size="md">Select AI Models</Heading>
      </HStack>
    </CardHeader>
    <CardBody>
      <CheckboxGroup value={selectedModels} onChange={setSelectedModels}>
        <Stack spacing={3}>
          <Checkbox value="gpt-4o">
            <VStack align="start" spacing={0}>
              <Text fontWeight="bold">GPT-4o (OpenAI)</Text>
              <Text fontSize="sm" color="gray.600">
                Advanced model with strong automotive accessibility knowledge
              </Text>
            </VStack>
          </Checkbox>
          <Checkbox value="claude-opus-4">
            <VStack align="start" spacing={0}>
              <Text fontWeight="bold">Claude Opus 4 (Anthropic)</Text>
              <Text fontSize="sm" color="gray.600">
                Detailed infotainment code analysis with safety focus
              </Text>
            </VStack>
          </Checkbox>
          <Checkbox value="Deepseek-V3">
            <VStack align="start" spacing={0}>
              <Text fontWeight="bold">DeepSeek V3</Text>
              <Text fontSize="sm" color="gray.600">
                Latest model with enhanced automotive UI reasoning
              </Text>
            </VStack>
          </Checkbox>
        </Stack>
      </CheckboxGroup>
    </CardBody>
  </Card>
);

// Infotainment Insights Modal
export const InfotainmentInsightsModal = ({ isOpen, onClose, infotainmentInsights }) => (
  <Modal isOpen={isOpen} onClose={onClose} size="6xl">
    <ModalOverlay />
    <ModalContent>
      <ModalHeader>
        <HStack>
          <FaChartLine />
          <Text>Infotainment Accessibility Insights</Text>
        </HStack>
      </ModalHeader>
      <ModalCloseButton />
      <ModalBody>
        {infotainmentInsights && (
          <VStack spacing={6} align="stretch">
            {/* Safety Assessment */}
            <Card>
              <CardHeader>
                <HStack>
                  <FaExclamationTriangle color="red" />
                  <Heading size="md">Safety Assessment</Heading>
                </HStack>
              </CardHeader>
              <CardBody>
                <StatGroup>
                  <Stat>
                    <StatLabel>Safety Critical Issues</StatLabel>
                    <StatNumber color="red.500">
                      {infotainmentInsights.safety_assessment.total_safety_critical}
                    </StatNumber>
                    <StatHelpText>Immediate attention required</StatHelpText>
                  </Stat>
                  <Stat>
                    <StatLabel>Eyes-Off-Road Violations</StatLabel>
                    <StatNumber color="orange.500">
                      {infotainmentInsights.safety_assessment.eyes_off_road_violations.length}
                    </StatNumber>
                    <StatHelpText>&gt;2s individual glances</StatHelpText>
                  </Stat>
                  <Stat>
                    <StatLabel>Task Time Violations</StatLabel>
                    <StatNumber color="yellow.500">
                      {infotainmentInsights.safety_assessment.task_time_violations.length}
                    </StatNumber>
                    <StatHelpText>&gt;12s total task time</StatHelpText>
                  </Stat>
                </StatGroup>
              </CardBody>
            </Card>

            {/* Interaction Analysis */}
            <Card>
              <CardHeader>
                <HStack>
                  <FaHandPaper />
                  <Heading size="md">Interaction Method Analysis</Heading>
                </HStack>
              </CardHeader>
              <CardBody>
                <SimpleGrid columns={4} spacing={4}>
                  <Stat>
                    <StatLabel>
                      <HStack>
                        <FaHandPaper />
                        <Text>Touch Issues</Text>
                      </HStack>
                    </StatLabel>
                    <StatNumber>{infotainmentInsights.interaction_analysis.touch_issues}</StatNumber>
                  </Stat>
                  <Stat>
                    <StatLabel>
                      <HStack>
                        <FaMicrophone />
                        <Text>Voice Issues</Text>
                      </HStack>
                    </StatLabel>
                    <StatNumber>{infotainmentInsights.interaction_analysis.voice_issues}</StatNumber>
                  </Stat>
                  <Stat>
                    <StatLabel>
                      <HStack>
                        <FaGamepad />
                        <Text>Physical Button Issues</Text>
                      </HStack>
                    </StatLabel>
                    <StatNumber>{infotainmentInsights.interaction_analysis.physical_button_issues}</StatNumber>
                  </Stat>
                  <Stat>
                    <StatLabel>
                      <HStack>
                        <FaCar />
                        <Text>Steering Wheel Issues</Text>
                      </HStack>
                    </StatLabel>
                    <StatNumber>{infotainmentInsights.interaction_analysis.steering_wheel_issues}</StatNumber>
                  </Stat>
                </SimpleGrid>
              </CardBody>
            </Card>

            {/* Standards Compliance */}
            <Card>
              <CardHeader>
                <HStack>
                  <FaShieldAlt />
                  <Heading size="md">Standards Compliance</Heading>
                </HStack>
              </CardHeader>
              <CardBody>
                <SimpleGrid columns={3} spacing={4}>
                  <Box>
                    <Text fontWeight="bold">WCAG Violations</Text>
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
                    <Text fontWeight="bold">Automotive Standards</Text>
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
                    <Text fontWeight="bold">Compliance Rate</Text>
                    <CircularProgress
                      value={85}
                      color="green.400"
                      size="80px"
                    >
                      <CircularProgressLabel>85%</CircularProgressLabel>
                    </CircularProgress>
                  </Box>
                </SimpleGrid>
              </CardBody>
            </Card>

            {/* Recommendations */}
            <Card>
              <CardHeader>
                <HStack>
                  <FaLightbulb />
                  <Heading size="md">Recommendations</Heading>
                </HStack>
              </CardHeader>
              <CardBody>
                <VStack align="stretch" spacing={3}>
                  {infotainmentInsights.recommendations.map((rec, index) => (
                    <Alert key={index} status={rec.priority === 'critical' ? 'error' : rec.priority === 'high' ? 'warning' : 'info'}>
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
          </VStack>
        )}
      </ModalBody>
    </ModalContent>
  </Modal>
);

// Enhanced Diff View Modal
export const DiffViewModal = ({ isOpen, onClose, codeView }) => (
  <Modal isOpen={isOpen} onClose={onClose} size="6xl">
    <ModalOverlay />
    <ModalContent>
      <ModalHeader>
        <VStack align="start" spacing={1}>
          <Text>Code Diff View - {codeView.issue?.file}:{codeView.issue?.line}</Text>
          {codeView.issue && (
            <HStack>
              <Badge colorScheme={getSeverityColor(codeView.issue.severity)}>
                {codeView.issue.severity}
              </Badge>
              {codeView.issue.safety_critical && (
                <Badge colorScheme="red" variant="solid">
                  <HStack spacing={1}>
                    <FaExclamationTriangle />
                    <Text>SAFETY CRITICAL</Text>
                  </HStack>
                </Badge>
              )}
              <Badge colorScheme="blue">
                {formatIssueType(codeView.issue.type)}
              </Badge>
            </HStack>
          )}
        </VStack>
      </ModalHeader>
      <ModalCloseButton />
      <ModalBody>
        {codeView.issue && (
          <VStack spacing={4}>
            {/* Issue Details */}
            <Box width="full" p={4} bg="gray.50" borderRadius="md">
              <VStack align="start" spacing={2}>
                <Text fontWeight="bold">Issue Description:</Text>
                <Text>{codeView.issue.description}</Text>

                {/* Automotive Metrics */}
                {codeView.issue.automotive_metrics && (
                  <HStack spacing={4} mt={2}>
                    <Stat size="sm">
                      <StatLabel>Eyes Off Road</StatLabel>
                      <StatNumber fontSize="md">
                        {codeView.issue.automotive_metrics.eyes_off_road_time}s
                      </StatNumber>
                    </Stat>
                    <Stat size="sm">
                      <StatLabel>Glance Count</StatLabel>
                      <StatNumber fontSize="md">
                        {codeView.issue.automotive_metrics.glance_count}
                      </StatNumber>
                    </Stat>
                    <Stat size="sm">
                      <StatLabel>Task Time</StatLabel>
                      <StatNumber fontSize="md">
                        {codeView.issue.automotive_metrics.task_time}s
                      </StatNumber>
                    </Stat>
                  </HStack>
                )}

                {/* Standards Violated */}
                <Box>
                  <Text fontWeight="bold">Standards Violated:</Text>
                  <HStack wrap="wrap" spacing={2} mt={1}>
                    {codeView.issue.wcag_criteria?.map((criteria, i) => (
                      <Badge key={i} colorScheme="blue">{criteria}</Badge>
                    ))}
                    {codeView.issue.iso15008_criteria?.map((criteria, i) => (
                      <Badge key={i} colorScheme="green">ISO15008: {criteria}</Badge>
                    ))}
                    {codeView.issue.nhtsa_criteria?.map((criteria, i) => (
                      <Badge key={i} colorScheme="orange">NHTSA: {criteria}</Badge>
                    ))}
                  </HStack>
                </Box>
              </VStack>
            </Box>

            {/* Code Diff */}
            <Box height="400px" width="full">
              <DiffEditor
                original={codeView.issue.original_code || '// No original code available'}
                modified={codeView.issue.suggested_fix || '// No suggested fix available'}
                language="javascript"
                theme="vs-light"
                options={{
                  readOnly: true,
                  minimap: { enabled: false },
                  wordWrap: 'on'
                }}
              />
            </Box>
          </VStack>
        )}
      </ModalBody>
    </ModalContent>
  </Modal>
);