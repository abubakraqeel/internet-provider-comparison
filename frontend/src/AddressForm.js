// src/AddressForm.js
import React, { useState, useEffect } from 'react';
import {
  Box,
  FormControl,
  FormLabel,
  Input,
  Button,
  VStack,
  Heading,
  Alert,
  AlertIcon
} from '@chakra-ui/react';

// No localStorage key needed here; App.js will manage address persistence related to searches.

function AddressForm({ onSubmitAddress, isLoading, currentAddress }) { // Renamed prop from initialValues
  const [strasse, setStrasse] = useState('');
  const [hausnummer, setHausnummer] = useState('');
  const [postleitzahl, setPostleitzahl] = useState('');
  const [stadt, setStadt] = useState('');
  const land = 'DE'; // Kept as constant
  const [error, setError] = useState('');

  // Effect to pre-fill form fields when the 'currentAddress' prop (from App.js) changes.
  // This happens on initial load if localStorage has data, or if App.js updates it.
  useEffect(() => {
    if (currentAddress) {
      setStrasse(currentAddress.strasse || '');
      setHausnummer(currentAddress.hausnummer || '');
      setPostleitzahl(currentAddress.postleitzahl || '');
      setStadt(currentAddress.stadt || '');
      // console.log("AddressForm: Fields updated from currentAddress prop", currentAddress);
    } else {
      // If currentAddress is null (e.g., first ever load, or cleared state)
      // You might want to clear fields or not, depending on desired UX.
      // For now, let's clear them if currentAddress becomes null.
      setStrasse('');
      setHausnummer('');
      setPostleitzahl('');
      setStadt('');
    }
  }, [currentAddress]); // Re-run ONLY if currentAddress prop changes

  const handleSubmit = (event) => {
    // console.log("AddressForm: handleSubmit triggered!");
    event.preventDefault();
    
    if (!strasse || !hausnummer || !postleitzahl || !stadt) {
      setError('All address fields (Street, House No., PLZ, City) are required.');
      return;
    }
    setError('');

    const addressDetails = {
      strasse,
      hausnummer,
      postleitzahl,
      stadt,
      land,
    };
    // App.js (via onSubmitAddress) will now handle saving this to localStorage
    // as part of the search submission process.
    onSubmitAddress(addressDetails);
  };

  return (
    <Box 
      p={6} 
      borderWidth="1px" 
      borderRadius="lg" 
      boxShadow="md" 
      w={{ base: "90%", md: "xl" }}
      mx="auto"
    >
      <Heading as="h2" size="lg" mb={6} textAlign="center">
        Find Internet Offers
      </Heading>
      
      {error && (
        <Alert status="error" mb={4}>
          <AlertIcon />
          {error}
        </Alert>
      )}

      <form onSubmit={handleSubmit}>
        <VStack spacing={4}>
          <FormControl isRequired>
            <FormLabel htmlFor="strasse">Street (Straße)</FormLabel>
            <Input
              id="strasse"
              placeholder="e.g., Musterstraße"
              value={strasse}
              onChange={(e) => setStrasse(e.target.value)}
            />
          </FormControl>

          <FormControl isRequired>
            <FormLabel htmlFor="hausnummer">House Number (Hausnummer)</FormLabel>
            <Input
              id="hausnummer"
              placeholder="e.g., 123a"
              value={hausnummer}
              onChange={(e) => setHausnummer(e.target.value)}
            />
          </FormControl>

          <FormControl isRequired>
            <FormLabel htmlFor="postleitzahl">Postal Code (PLZ)</FormLabel>
            <Input
              id="postleitzahl"
              placeholder="e.g., 10115"
              value={postleitzahl}
              onChange={(e) => setPostleitzahl(e.target.value)}
            />
          </FormControl>

          <FormControl isRequired>
            <FormLabel htmlFor="stadt">City (Stadt)</FormLabel>
            <Input
              id="stadt"
              placeholder="e.g., Berlin"
              value={stadt}
              onChange={(e) => setStadt(e.target.value)}
            />
          </FormControl>
          
          <Button
            type="submit"
            colorScheme="teal"
            size="lg"
            width="full"
            isLoading={isLoading}
            loadingText="Searching..."
          >
            Search Offers
          </Button>
        </VStack>
      </form>
    </Box>
  );
}

export default AddressForm;