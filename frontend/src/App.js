// src/App.js
import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { Routes, Route, Link as RouterLink } from 'react-router-dom';
import {
  Box,
  VStack,
  Heading,
  Spinner,
  Alert,
  AlertIcon,
  Text,
  HStack,
  Select,
  CheckboxGroup,
  Checkbox,
  Stack,
  Button as ChakraButton,
  FormControl,
  FormLabel,
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalFooter, ModalBody, ModalCloseButton,
  Input as ChakraInput,
  useDisclosure,
  useClipboard,
  Link as ChakraLink
} from '@chakra-ui/react';

import AddressForm from './AddressForm';
import OfferList from './OfferList';
import SharedResultsPage from './SharedResultsPage'; // Ensure this path is correct

const LOCAL_STORAGE_ADDRESS_KEY = 'lastSearchAddress';
const LOCAL_STORAGE_LAST_RESULTS_KEY = 'lastSearchResults';

// --- Helper: Get unique values for filter options ---
const getUniqueValues = (offers, key) => {
  if (!offers || offers.length === 0) return [];
  const values = offers
    .map(offer => offer[key] !== null && offer[key] !== undefined ? String(offer[key]) : '')
    .filter(Boolean);
  return [...new Set(values)].sort((a, b) => {
    const numA = parseFloat(a);
    const numB = parseFloat(b);
    if (!isNaN(numA) && !isNaN(numB)) {
      return numA - numB;
    }
    return a.localeCompare(b);
  });
};

function App() {
  const [offers, setOffers] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);

  const [sortBy, setSortBy] = useState('');
  const [filterConnectionTypes, setFilterConnectionTypes] = useState([]);
  const [filterProviderNames, setFilterProviderNames] = useState([]);
  const [filterContractTerms, setFilterContractTerms] = useState([]);

  const { isOpen: isShareModalOpen, onOpen: onShareModalOpen, onClose: onShareModalClose } = useDisclosure();
  const [shareableLink, setShareableLink] = useState('');
  const { onCopy: onCopyShareLink, hasCopied: hasCopiedShareLink } = useClipboard(shareableLink);
  const [isSharing, setIsSharing] = useState(false);
  const [shareError, setShareError] = useState(null);

  // This state will hold the address for the current/last search, also used to prefill form
  const [currentSearchAddress, setCurrentSearchAddress] = useState(null);

  // Load initial state from localStorage when App component mounts
  useEffect(() => {
    try {
      const storedAddress = localStorage.getItem(LOCAL_STORAGE_ADDRESS_KEY);
      if (storedAddress) {
        setCurrentSearchAddress(JSON.parse(storedAddress));
        // console.log("App.js: Loaded initial address from localStorage", JSON.parse(storedAddress));
      }

      const storedResults = localStorage.getItem(LOCAL_STORAGE_LAST_RESULTS_KEY);
      if (storedResults) {
        const parsedResults = JSON.parse(storedResults);
        if (parsedResults.offers && Array.isArray(parsedResults.offers)) setOffers(parsedResults.offers);
        if (typeof parsedResults.hasSearched === 'boolean') setHasSearched(parsedResults.hasSearched);
        if (parsedResults.sortBy) setSortBy(parsedResults.sortBy);
        if (parsedResults.filterConnectionTypes) setFilterConnectionTypes(parsedResults.filterConnectionTypes);
        if (parsedResults.filterProviderNames) setFilterProviderNames(parsedResults.filterProviderNames);
        if (parsedResults.filterContractTerms) setFilterContractTerms(parsedResults.filterContractTerms);
        // console.log("App.js: Loaded last search results from localStorage");
      }
    } catch (e) {
      console.error("App.js: Error loading from localStorage on mount", e);
      // Optionally clear corrupted data
      // localStorage.removeItem(LOCAL_STORAGE_ADDRESS_KEY);
      // localStorage.removeItem(LOCAL_STORAGE_LAST_RESULTS_KEY);
    }
  }, []); // Empty dependency array means this runs once on mount

  const handleAddressSubmit = useCallback(async (addressDetailsFromForm) => {
    setIsLoading(true);
    setError(null);
    setHasSearched(true); 

    // Update current search address state AND save it to localStorage immediately
    setCurrentSearchAddress(addressDetailsFromForm);
    try {
      localStorage.setItem(LOCAL_STORAGE_ADDRESS_KEY, JSON.stringify(addressDetailsFromForm));
      // console.log("App.js: Saved new search address to localStorage", addressDetailsFromForm);
    } catch (e) {
      console.error("App.js: Error saving address to localStorage", e);
    }

    // Resetting filters on new search is good practice
    setSortBy('');
    setFilterConnectionTypes([]);
    setFilterProviderNames([]);
    setFilterContractTerms([]);
    
    // Clear previous offers before fetching new ones to avoid flicker of old data if fetch is slow
    setOffers([]); 

    try {
      const jsonBody = JSON.stringify(addressDetailsFromForm);
      const response = await fetch('/api/offers', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: jsonBody,
      });

      if (!response.ok) {
        let errorData;
        const responseText = await response.text();
        console.error("handleAddressSubmit: Server responded with an error. Raw response text:", responseText);
        try { errorData = JSON.parse(responseText); }
        catch (e) { errorData = { message: `HTTP error! Status: ${response.status}. Response: ${responseText.substring(0, 200)}...` }; }
        
        localStorage.removeItem(LOCAL_STORAGE_LAST_RESULTS_KEY); // Clear stored results on error
        throw new Error(errorData.message || `HTTP error! Status: ${response.status}`);
      }
      const data = await response.json();
      setOffers(data); // Set new offers

      // Save successful search results to localStorage (including reset filters/sort for this new search)
      try {
        const resultsToStore = {
          offers: data,
          hasSearched: true,
          sortBy: '', 
          filterConnectionTypes: [],
          filterProviderNames: [],
          filterContractTerms: [],
        };
        localStorage.setItem(LOCAL_STORAGE_LAST_RESULTS_KEY, JSON.stringify(resultsToStore));
        // console.log("App.js: Saved new search results to localStorage", resultsToStore);
      } catch (e) {
        console.error("App.js: Error saving search results to localStorage", e);
      }

    } catch (err) {
      console.error("handleAddressSubmit: Error caught in try-catch block:", err);
      setError(err.message || 'Failed to fetch offers. Please try again.');
      // Offers already cleared or will be empty due to error, ensure stored results are also cleared
      localStorage.removeItem(LOCAL_STORAGE_LAST_RESULTS_KEY); 
    } finally {
      setIsLoading(false);
    }
  }, []); // Dependencies are empty as we manage internal state explicitly or it's reset.

  // Effect to save filter/sort changes to localStorage
  useEffect(() => {
    // Only save if a search has been made and there are offers to apply filters to
    if (hasSearched && offers.length > 0) { 
      try {
        // Retrieve existing stored results to preserve offers & hasSearched status
        const storedResults = JSON.parse(localStorage.getItem(LOCAL_STORAGE_LAST_RESULTS_KEY) || '{}');
        const dataToStore = {
          ...storedResults, // This will include offers and hasSearched from the last successful search
          offers: offers,   // Ensure current offers are part of what's saved with filters
          hasSearched: hasSearched, // And current search status
          sortBy: sortBy,
          filterConnectionTypes: filterConnectionTypes,
          filterProviderNames: filterProviderNames,
          filterContractTerms: filterContractTerms,
        };
        localStorage.setItem(LOCAL_STORAGE_LAST_RESULTS_KEY, JSON.stringify(dataToStore));
        // console.log("App.js: Updated filters/sort in localStorage", dataToStore);
      } catch (e) {
        console.error("App.js: Error updating filters/sort in localStorage", e);
      }
    }
  }, [sortBy, filterConnectionTypes, filterProviderNames, filterContractTerms, offers, hasSearched]);


  const availableConnectionTypes = useMemo(() => getUniqueValues(offers, 'connectionType'), [offers]);
  const availableProviderNames = useMemo(() => getUniqueValues(offers, 'providerName'), [offers]);
  const availableContractTerms = useMemo(() => getUniqueValues(offers, 'contractTermMonths'), [offers]);

  const displayedOffers = useMemo(() => {
    let processedOffers = [...offers]; 
    if (filterConnectionTypes.length > 0) {
      processedOffers = processedOffers.filter(offer => offer.connectionType && filterConnectionTypes.includes(offer.connectionType));
    }
    if (filterProviderNames.length > 0) {
      processedOffers = processedOffers.filter(offer => offer.providerName && filterProviderNames.includes(offer.providerName));
    }
    if (filterContractTerms.length > 0) {
      processedOffers = processedOffers.filter(offer => offer.contractTermMonths !== null && offer.contractTermMonths !== undefined && filterContractTerms.includes(String(offer.contractTermMonths)));
    }
    if (sortBy === 'price_asc') { processedOffers.sort((a, b) => (a.monthlyPriceEur ?? Infinity) - (b.monthlyPriceEur ?? Infinity)); }
    else if (sortBy === 'price_desc') { processedOffers.sort((a, b) => (b.monthlyPriceEur ?? -Infinity) - (a.monthlyPriceEur ?? -Infinity)); }
    else if (sortBy === 'speed_desc') { processedOffers.sort((a, b) => (b.downloadSpeedMbps ?? -Infinity) - (a.downloadSpeedMbps ?? -Infinity)); }
    else if (sortBy === 'speed_asc') { processedOffers.sort((a, b) => (a.downloadSpeedMbps ?? Infinity) - (b.downloadSpeedMbps ?? Infinity)); }
    else if (sortBy === 'contract_asc') { processedOffers.sort((a,b) => (a.contractTermMonths ?? Infinity) - (b.contractTermMonths ?? Infinity)); }
    return processedOffers;
  }, [offers, sortBy, filterConnectionTypes, filterProviderNames, filterContractTerms]);

  const resetFiltersAndSort = () => {
    setSortBy('');
    setFilterConnectionTypes([]);
    setFilterProviderNames([]);
    setFilterContractTerms([]);
  };

  const handleShareResults = async () => {
    // ... (handleShareResults logic remains the same - it uses 'displayedOffers') ...
    console.log("handleShareResults: Triggered. Offers to share:", displayedOffers);
    if (displayedOffers.length === 0) {
      setShareError("No offers to share.");
      onShareModalOpen();
      return;
    }
    setIsSharing(true);
    setShareError(null);
    setShareableLink('');
    try {
      const requestBody = JSON.stringify(displayedOffers);
      console.log("handleShareResults: Sending POST to /api/share with body:", requestBody);
      const response = await fetch('/api/share', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: requestBody
      });
      console.log("handleShareResults: Received response from /api/share. Status:", response.status, "StatusText:", response.statusText);

      if (!response.ok) {
        let errorData;
        const responseText = await response.text();
        console.error("handleShareResults: Server responded with an error. Raw response text:", responseText);
        try { errorData = JSON.parse(responseText); } 
        catch (e) { errorData = { error: `Server error: ${response.status} ${response.statusText}. Response: ${responseText.substring(0, 200)}...` }; }
        throw new Error(errorData.error || "Failed to create share link.");
      }
      const result = await response.json();
      console.log("handleShareResults: Successfully created share link. Server response:", result);
      if (!result.shareId) {
        console.error("handleShareResults: Server response OK, but 'shareId' is missing in the result:", result);
        throw new Error("Failed to create share link: Invalid response from server (missing shareId).");
      }
      const fullShareLink = `${window.location.origin}/share/${result.shareId}`;
      setShareableLink(fullShareLink);
    } catch (err) {
      console.error("handleShareResults: Error caught in try-catch block:", err);
      setShareError(err.message || "Could not create share link.");
    } finally {
      console.log("handleShareResults: Finally block executing.");
      setIsSharing(false);
      onShareModalOpen();
    }
  };

  const ComparisonPage = () => (
    <VStack spacing={8} align="stretch">
      <Heading as="h1" size="2xl" textAlign="center" color="teal.600" my={8}>
        Internet Provider Comparison
      </Heading>
      <AddressForm
        onSubmitAddress={handleAddressSubmit}
        isLoading={isLoading}
        currentAddress={currentSearchAddress} // Pass the App.js managed current address
      />

      {!isLoading && !error && hasSearched && offers.length > 0 && (
        <Box p={5} borderWidth="1px" borderRadius="lg" bg="white" boxShadow="lg" mt={6}>
          <VStack spacing={5} align="stretch">
            <Heading as="h3" size="md" color="gray.700">Sort & Filter Results</Heading>
            <FormControl>
              <FormLabel htmlFor="sort-by" fontSize="sm" fontWeight="bold">Sort By:</FormLabel>
              <Select id="sort-by" placeholder="Default Order" value={sortBy} onChange={(e) => setSortBy(e.target.value)} size="sm" borderRadius="md">
                <option value="price_asc">Price: Low to High</option>
                <option value="price_desc">Price: High to Low</option>
                <option value="speed_desc">Speed: High to Low</option>
                <option value="speed_asc">Speed: Low to High</option>
                <option value="contract_asc">Contract: Shortest First</option>
              </Select>
            </FormControl>
            {availableConnectionTypes.length > 0 && (
              <FormControl>
                <FormLabel fontSize="sm" fontWeight="bold">Connection Type:</FormLabel>
                <CheckboxGroup colorScheme="teal" value={filterConnectionTypes} onChange={setFilterConnectionTypes}>
                  <Stack spacing={3} direction={{ base: "column", sm: "row" }} wrap="wrap">
                    {availableConnectionTypes.map(type => (<Checkbox key={type} value={type} size="sm">{type || "N/A"}</Checkbox>))}
                  </Stack>
                </CheckboxGroup>
              </FormControl>
            )}
            {availableProviderNames.length > 0 && (
              <FormControl>
                <FormLabel fontSize="sm" fontWeight="bold">Provider:</FormLabel>
                <CheckboxGroup colorScheme="purple" value={filterProviderNames} onChange={setFilterProviderNames}>
                  <Stack spacing={3} direction={{ base: "column", sm: "row" }} wrap="wrap">
                    {availableProviderNames.map(name => (<Checkbox key={name} value={name} size="sm">{name || "N/A"}</Checkbox>))}
                  </Stack>
                </CheckboxGroup>
              </FormControl>
            )}
            {availableContractTerms.length > 0 && (
              <FormControl>
                <FormLabel fontSize="sm" fontWeight="bold">Contract Term (Months):</FormLabel>
                <CheckboxGroup colorScheme="orange" value={filterContractTerms} onChange={setFilterContractTerms}>
                  <Stack spacing={3} direction={{ base: "column", sm: "row" }} wrap="wrap">
                    {availableContractTerms.map(term => (<Checkbox key={term} value={term} size="sm">{term || "N/A"} months</Checkbox>))}
                  </Stack>
                </CheckboxGroup>
              </FormControl>
            )}
            <ChakraButton size="sm" variant="outline" colorScheme="gray" onClick={resetFiltersAndSort} mt={3} alignSelf="flex-start">
              Reset Filters & Sort
            </ChakraButton>
          </VStack>
        </Box>
      )}

      {isLoading && ( <Box textAlign="center" mt={10}> <Spinner size="xl" color="teal.500" /> <Heading as="h3" size="md" mt={4}>Fetching offers...</Heading> </Box> )}
      {error && ( <Alert status="error" mt={6} variant="solid"> <AlertIcon /> {error} </Alert> )}
      
      {!isLoading && !error && hasSearched && (
        <Box mt={6}>
          <HStack justifyContent="space-between" alignItems="center" mb={4}>
            <Heading as="h2" size="lg">
              Comparison Results
              {displayedOffers.length > 0 && ` (${displayedOffers.length} offers found)`}
              {offers.length > 0 && displayedOffers.length !== offers.length && ` (from ${offers.length} total)`}
            </Heading>
            {displayedOffers.length > 0 && (
              <ChakraButton colorScheme="green" onClick={handleShareResults} size="sm">
                Share These Results
              </ChakraButton>
            )}
          </HStack>
          <OfferList offers={displayedOffers} />
        </Box>
      )}
      
      {!isLoading && !hasSearched && !error && ( <Box textAlign="center" mt={10} p={5}> <Text fontSize="lg" color="gray.500">Enter your address above to find internet offers.</Text> </Box> )}
    </VStack>
  );

  return (
    <Box p={5} minHeight="100vh" bg="gray.50" maxW="container.xl" mx="auto">
      <Routes>
        <Route path="/" element={<ComparisonPage />} />
        <Route path="/share/:shareId" element={<SharedResultsPage />} />
        <Route path="*" element={<Box textAlign="center" mt={20}><Heading>404 - Page Not Found</Heading><ChakraButton as={RouterLink} to="/" colorScheme="teal" mt={4}>Go Home</ChakraButton></Box>} />
      </Routes>

      <Modal isOpen={isShareModalOpen} onClose={onShareModalClose} isCentered>
        <ModalOverlay />
        <ModalContent mx={4}>
          <ModalHeader>Share Results</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            {shareError && <Alert status="error" mb={3} variant="subtle"><AlertIcon />{shareError}</Alert>}
            {shareableLink && !shareError && (
              <VStack spacing={3} align="stretch">
                <Text fontSize="sm">Share this link with others:</Text>
                <HStack width="100%">
                  <ChakraInput value={shareableLink} isReadOnly pr="4.5rem" size="sm"/>
                  <ChakraButton size="sm" onClick={onCopyShareLink}>
                    {hasCopiedShareLink ? "Copied!" : "Copy"}
                  </ChakraButton>
                </HStack>
                <ChakraLink 
                    href={`whatsapp://send?text=Check%20out%20these%20internet%20offers:%20${encodeURIComponent(shareableLink)}`}
                    isExternal
                    width="full"
                >
                    <ChakraButton colorScheme="whatsapp" width="full" size="sm"> 
                        Share on WhatsApp
                    </ChakraButton>
                </ChakraLink>
              </VStack>
            )}
            {isSharing && <Spinner size="md" />}
          </ModalBody>
          <ModalFooter>
            <ChakraButton variant="ghost" onClick={onShareModalClose} size="sm">Close</ChakraButton>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
}

export default App;