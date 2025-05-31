import React from 'react';
import {
  Box,
  VStack,
  HStack,
  Skeleton,
  SkeletonText,
  Card,
  CardHeader,
  CardBody,
  Heading,
  Stack,
  Alert,
  AlertIcon,
  Text,
  Spinner,
  Badge,
  Progress
} from '@chakra-ui/react';

// Enhanced Loading Skeleton Component
export const LoadingSkeleton = ({ type = 'card', lines = 3, height = '20px' }) => {
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

  if (type === 'text') {
    return <Skeleton height={height} />;
  }

  return <Skeleton height={height} />;
};

// Models Loading Component
export const ModelsLoadingCard = () => (
  <Card>
    <CardHeader>
      <Heading size="sm">Select AI Models</Heading>
    </CardHeader>
    <CardBody>
      <VStack spacing={4} align="stretch">
        <HStack>
          <Spinner size="sm" />
          <Text fontSize="sm" color="gray.500">Loading available AI models...</Text>
        </HStack>
        <Stack spacing={3}>
          <LoadingSkeleton type="checkbox" />
          <LoadingSkeleton type="checkbox" />
          <LoadingSkeleton type="checkbox" />
          <LoadingSkeleton type="checkbox" />
        </Stack>
      </VStack>
    </CardBody>
  </Card>
);

// Standards Loading Component
export const StandardsLoadingCard = () => (
  <Card>
    <CardHeader>
      <Heading size="sm">Accessibility Standards</Heading>
    </CardHeader>
    <CardBody>
      <VStack spacing={4} align="stretch">
        <HStack>
          <Spinner size="sm" />
          <Text fontSize="sm" color="gray.500">Loading accessibility standards...</Text>
        </HStack>
        <Stack spacing={3}>
          <LoadingSkeleton type="checkbox" />
          <LoadingSkeleton type="checkbox" />
          <LoadingSkeleton type="checkbox" />
          <LoadingSkeleton type="checkbox" />
          <LoadingSkeleton type="checkbox" />
        </Stack>
      </VStack>
    </CardBody>
  </Card>
);

// Data Loading Alert
export const DataLoadingAlert = ({ isLoading, hasError, errorMessage }) => {
  if (!isLoading && !hasError) return null;

  if (hasError) {
    return (
      <Alert status="warning" borderRadius="md">
        <AlertIcon />
        <VStack align="start" spacing={1} flex="1">
          <Text fontWeight="bold">Connection Issue</Text>
          <Text fontSize="sm">
            {errorMessage || 'Failed to load some data from server. Using cached defaults.'}
          </Text>
        </VStack>
      </Alert>
    );
  }

  return (
    <Alert status="info" borderRadius="md">
      <AlertIcon />
      <HStack spacing={2} flex="1">
        <Spinner size="sm" />
        <VStack align="start" spacing={0} flex="1">
          <Text fontWeight="bold">Loading Configuration</Text>
          <Text fontSize="sm" color="gray.600">
            Fetching AI models and accessibility standards...
          </Text>
        </VStack>
      </HStack>
    </Alert>
  );
};

// Analysis Status Component
export const AnalysisStatusCard = ({ status, progress, message, details }) => {
  const getStatusColor = (status) => {
    switch (status) {
      case 'uploading': return 'blue';
      case 'analyzing': return 'orange';
      case 'completed': return 'green';
      case 'failed': return 'red';
      default: return 'gray';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'uploading': return 'Uploading Files';
      case 'analyzing': return 'Analyzing Code';
      case 'completed': return 'Analysis Complete';
      case 'failed': return 'Analysis Failed';
      default: return 'Processing';
    }
  };

  if (!status) return null;

  return (
    <Card borderColor={`${getStatusColor(status)}.200`} bg={`${getStatusColor(status)}.50`}>
      <CardBody>
        <VStack spacing={3} align="stretch">
          <HStack justify="space-between">
            <HStack>
              <Badge colorScheme={getStatusColor(status)} variant="solid">
                {getStatusText(status)}
              </Badge>
              {status === 'analyzing' && <Spinner size="sm" />}
            </HStack>
            {progress && (
              <Text fontSize="sm" color="gray.600">
                {progress}%
              </Text>
            )}
          </HStack>

          {message && (
            <Text fontSize="sm" fontWeight="medium">
              {message}
            </Text>
          )}

          {details && (
            <Text fontSize="xs" color="gray.600">
              {details}
            </Text>
          )}

          {status === 'analyzing' && (
            <Box>
              <Text fontSize="xs" color="gray.500" mb={2}>
                Analysis in progress...
              </Text>
              <Progress
                isIndeterminate
                colorScheme={getStatusColor(status)}
                size="sm"
                borderRadius="full"
              />
            </Box>
          )}
        </VStack>
      </CardBody>
    </Card>
  );
};

// Connection Status Indicator
export const ConnectionStatus = ({ isLoading, hasError }) => {
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