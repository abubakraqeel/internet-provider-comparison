// src/SharedResultsPage.js
import React, { useState, useEffect } from 'react';
import { useParams, Link as RouterLink } from 'react-router-dom';
import { Box, Heading, Spinner, Alert, AlertIcon, VStack, Button as ChakraButton, Text } from '@chakra-ui/react';
import OfferList from './OfferList'; // Reuse your OfferList component

function SharedResultsPage() {
  const { shareId } = useParams(); // Get shareId from URL
  const [offers, setOffers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!shareId) {
      setError("No Share ID provided.");
      setIsLoading(false);
      return;
    }

    const fetchSharedOffers = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch(`http://localhost:5001/api/share/${shareId}`); // Use correct backend port
        if (!response.ok) {
          let errorData;
          try { errorData = await response.json(); }
          catch (e) { errorData = { message: `HTTP error! Status: ${response.status}` }; }
          throw new Error(errorData.message || `HTTP error! Status: ${response.status}`);
        }
        const data = await response.json();
        setOffers(data);
      } catch (err) {
        setError(err.message || "Failed to load shared offers.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchSharedOffers();
  }, [shareId]); // Re-fetch if shareId changes (though it won't for this page typically)

  if (isLoading) {
    return (
      <Box textAlign="center" mt={20}>
        <Spinner size="xl" color="teal.500" />
        <Heading as="h3" size="md" mt={4}>Loading shared offers...</Heading>
      </Box>
    );
  }

  if (error) {
    return (
      <Box textAlign="center" mt={20} p={5}>
        <Alert status="error" variant="solid">
          <AlertIcon />
          {error}
        </Alert>
        <ChakraButton as={RouterLink} to="/" colorScheme="teal" mt={6}>
          Go to Homepage
        </ChakraButton>
      </Box>
    );
  }

  return (
    <Box p={5} minHeight="100vh" bg="gray.50">
      <VStack spacing={8} align="stretch" maxW="container.xl" mx="auto">
        <Heading as="h1" size="xl" textAlign="center" color="teal.600" my={8}>
          Shared Internet Offers
        </Heading>
        <OfferList offers={offers} />
        <Box textAlign="center" mt={6}>
            <ChakraButton as={RouterLink} to="/" colorScheme="teal">
                Search Again
            </ChakraButton>
        </Box>
      </VStack>
    </Box>
  );
}

export default SharedResultsPage;