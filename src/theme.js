import { extendTheme } from '@chakra-ui/react';

// Enhanced theme for infotainment focus
export const theme = extendTheme({
  config: {
    initialColorMode: 'light',
    useSystemColorMode: false,
  },
  colors: {
    automotive: {
      50: '#e6f7ff',
      100: '#bae7ff',
      200: '#91d5ff',
      300: '#69c0ff',
      400: '#40a9ff',
      500: '#1890ff',
      600: '#096dd9',
      700: '#0050b3',
      800: '#003a8c',
      900: '#002766',
    },
    safety: {
      50: '#fff2e8',
      100: '#ffd8bf',
      200: '#ffbe95',
      300: '#ffa46a',
      400: '#ff8a40',
      500: '#ff7016',
      600: '#e6590c',
      700: '#cc4202',
      800: '#b32b00',
      900: '#991400',
    }
  },
  components: {
    Button: {
      variants: {
        automotive: {
          bg: 'automotive.500',
          color: 'white',
          _hover: {
            bg: 'automotive.600',
          },
          _active: {
            bg: 'automotive.700',
          },
        },
        safety: {
          bg: 'safety.500',
          color: 'white',
          _hover: {
            bg: 'safety.600',
          },
          _active: {
            bg: 'safety.700',
          },
        }
      }
    },
    Badge: {
      variants: {
        automotive: {
          bg: 'automotive.500',
          color: 'white',
        },
        safety: {
          bg: 'safety.500',
          color: 'white',
        }
      }
    },
    Card: {
      baseStyle: {
        container: {
          boxShadow: 'md',
          borderRadius: 'lg',
          border: '1px solid',
          borderColor: 'gray.200',
        }
      }
    },
    Table: {
      variants: {
        automotive: {
          th: {
            borderBottomWidth: '2px',
            borderBottomColor: 'automotive.200',
            color: 'automotive.700',
            fontWeight: 'bold',
          },
          td: {
            borderBottomWidth: '1px',
            borderBottomColor: 'gray.200',
          }
        }
      }
    },
    Alert: {
      variants: {
        safety: {
          container: {
            bg: 'safety.50',
            borderColor: 'safety.200',
          },
          icon: {
            color: 'safety.500',
          }
        }
      }
    }
  },
  fonts: {
    heading: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    body: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  styles: {
    global: {
      body: {
        bg: 'gray.50',
        color: 'gray.800',
      },
    },
  },
});