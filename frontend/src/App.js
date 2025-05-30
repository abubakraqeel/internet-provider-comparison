// src/App.js
import React, { useState, useCallback } from 'react';
import { 
  Box,
  VStack,
  Heading,
  Spinner, // For loading state
  Alert,
  AlertIcon
  //extendTheme // For custom theme if needed later
} from '@chakra-ui/react';

import AddressForm from './AddressForm'; // Import your new component
// import OfferList from './OfferList'; // We'll create this next

// Optional: If you want to customize Chakra's theme (e.g., fonts, default colors)
// const theme = extendTheme({
//   fonts: {
//     heading: `'Open Sans', sans-serif`,
//     body: `'Raleway', sans-serif`,
//   },
// });

function App() {
  const [offers, setOffers] = useState([]); // To store fetched offers
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null); // For API errors

  // This function will be called by AddressForm when the form is submitted
  const handleAddressSubmit = useCallback(async (addressDetails) => {
    console.log('Address submitted to App:', addressDetails);
    setIsLoading(true);
    setError(null);
    setOffers([]); // Clear previous offers

    try {
      console.log('App.js: addressDetails before stringify:', addressDetails);
      console.log('App.js: typeof addressDetails:', typeof addressDetails);
      const jsonBody = JSON.stringify(addressDetails);
      console.log('App.js: JSON body to be sent:', jsonBody);

      // Your Flask backend API endpoint
      const response = await fetch('http://localhost:5001/api/offers', { // Assuming proxy is set up in package.json
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: jsonBody,
      });

      if (!response.ok) {
        // Try to get error message from backend if available
        let errorData;
        try {
            errorData = await response.json();
        } catch (e) {
            // If response is not JSON or other error
            errorData = { message: `HTTP error! Status: ${response.status}` };
        }
        throw new Error(errorData.message || `HTTP error! Status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Offers received from backend:', data);
      setOffers(data);

    } catch (err) {
      console.error("Failed to fetch offers:", err);
      setError(err.message || 'Failed to fetch offers. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, []); // Empty dependency array means this function is created once

  return (
    // If ChakraProvider is in index.js, you don't need it here again.
    // <ChakraProvider theme={theme}> {/* theme is optional */}
      <Box p={5} minHeight="100vh">
        <VStack spacing={8} align="stretch">
          <Heading as="h1" size="xl" textAlign="center" color="teal.500" my={6}>
            Internet Provider Comparison
          </Heading>

          <AddressForm onSubmitAddress={handleAddressSubmit} isLoading={isLoading} />

          {isLoading && (
            <Box textAlign="center" mt={10}>
              <Spinner size="xl" color="teal.500" thickness="4px" speed="0.65s" />
              <Heading as="h3" size="md" mt={4}>Fetching offers...</Heading>
            </Box>
          )}

          {error && (
            <Alert status="error" mt={6}>
              <AlertIcon />
              {error}
            </Alert>
          )}

          {!isLoading && !error && offers.length > 0 && (
            <Box mt={10}>
              <Heading as="h2" size="lg" mb={4}>Comparison Results ({offers.length} offers found)</Heading>
              {/* Placeholder for OfferList component */}
              <pre>{JSON.stringify(offers, null, 2)}</pre> 
              {/* <OfferList offers={offers} /> We'll build this next */}
            </Box>
          )}

          {!isLoading && !error && offers.length === 0 && (
            // Could add a message here if search was done but no offers returned,
            // but only after a search has actually been performed.
            // Need a state like `hasSearched` for that. For now, this is fine.
            <Box/>
          )}

        </VStack>
      </Box>
    // </ChakraProvider>
  );
}

export default App;