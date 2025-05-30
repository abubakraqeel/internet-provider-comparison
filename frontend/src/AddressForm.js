// src/AddressForm.js
import React, { useState } from 'react';
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

// The 'onSubmitAddress' prop will be a function passed down from App.js
function AddressForm({ onSubmitAddress, isLoading }) {
  // State for each input field
  // Using German keys to match what our Flask backend expects for the combined call
  const [strasse, setStrasse] = useState('');
  const [hausnummer, setHausnummer] = useState('');
  const [postleitzahl, setPostleitzahl] = useState('');
  const [stadt, setStadt] = useState('');
  //const [land, setLand] = useState('DE'); // Default to DE, can be input later if needed
  const land = 'DE';
  const [error, setError] = useState(''); // For form-level validation errors

  const handleSubmit = (event) => {
    console.log("AddressForm: handleSubmit triggered!");
    event.preventDefault(); // Prevent default form submission (page reload)
    
    // Basic validation
    if (!strasse || !hausnummer || !postleitzahl || !stadt) {
      setError('All address fields (Street, House No., PLZ, City) are required.');
      return;
    }
    setError(''); // Clear previous errors

    const addressDetails = {
      strasse,
      hausnummer,
      postleitzahl,
      stadt,
      land, // Include land if your backend route expects it for all providers
            // Or if any provider client specifically needs it from this common payload
    };
    onSubmitAddress(addressDetails); // Call the function passed from App.js
  };

  return (
    <Box 
      p={6} 
      borderWidth="1px" 
      borderRadius="lg" 
      boxShadow="md" 
      w={{ base: "90%", md: "xl" }} // Responsive width
      mx="auto" // Center the box
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
          
          {/* Optional: Input for Land/Country if needed dynamically 
          <FormControl>
            <FormLabel htmlFor="land">Country Code (Land)</FormLabel>
            <Input
              id="land"
              value={land}
              onChange={(e) => setLand(e.target.value.toUpperCase())} // Example to force uppercase
              maxLength={2}
            />
          </FormControl>
          */}

          <Button
            type="submit"
            colorScheme="teal"
            size="lg"
            width="full"
            isLoading={isLoading} // Show loading state on button
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