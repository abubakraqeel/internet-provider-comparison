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

  const handleAddressSubmit = useCallback(async (addressDetails) => {
    setIsLoading(true);
    setError(null);
    setOffers([]); 
    setHasSearched(true);
    setSortBy('');
    setFilterConnectionTypes([]);
    setFilterProviderNames([]);
    setFilterContractTerms([]);

    try {
      const jsonBody = JSON.stringify(addressDetails);
      const response = await fetch('/api/offers', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: jsonBody,
      });

      if (!response.ok) {
        let errorData;
        try { errorData = await response.json(); }
        catch (e) { errorData = { message: `HTTP error! Status: ${response.status}` }; }
        throw new Error(errorData.message || `HTTP error! Status: ${response.status}`);
      }
      const data = await response.json();
      setOffers(data);
    } catch (err) {
      setError(err.message || 'Failed to fetch offers. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, []); 

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
    if (displayedOffers.length === 0) {
      setShareError("No offers to share.");
      onShareModalOpen();
      return;
    }
    setIsSharing(true);
    setShareError(null);
    setShareableLink('');
    try {
      // *** UPDATED FETCH URL FOR CREATING SHARE LINK ***
      const response = await fetch('/api/share', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(displayedOffers)
      });
      if (!response.ok) {
        const errData = await response.json().catch(() => ({ error: "Failed to create share link (server error)." }));
        throw new Error(errData.error || "Failed to create share link.");
      }
      const result = await response.json();
      const fullShareLink = `${window.location.origin}/share/${result.shareId}`; // Assumes shareId is returned
      setShareableLink(fullShareLink);
    } catch (err) {
      setShareError(err.message || "Could not create share link.");
    } finally {
      setIsSharing(false);
      onShareModalOpen();
    }
  };

  const ComparisonPage = () => (
    <VStack spacing={8} align="stretch">
      <Heading as="h1" size="2xl" textAlign="center" color="teal.600" my={8}>
        Internet Provider Comparison
      </Heading>
      <AddressForm onSubmitAddress={handleAddressSubmit} isLoading={isLoading} />

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
                        Share on WhatsApp {/* Actual icon would require an icon library */}
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