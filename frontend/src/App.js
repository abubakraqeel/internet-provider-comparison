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
  RadioGroup,
  Radio,
} from '@chakra-ui/react';

import AddressForm from './AddressForm';
import OfferList from './OfferList';

const LOCAL_STORAGE_ADDRESS_KEY = 'lastSearchAddress';
const LOCAL_STORAGE_LAST_RESULTS_KEY = 'lastSearchResults';

const getUniqueValues = (offers, key, sortNumerically = true) => {
  if (!offers || offers.length === 0) return [];
  const values = offers
    .map(offer => offer[key] !== null && offer[key] !== undefined ? String(offer[key]) : '')
    .filter(Boolean);
  
  let uniqueValues = [...new Set(values)];

  if (sortNumerically) {
    uniqueValues.sort((a, b) => {
      const numA = parseFloat(a);
      const numB = parseFloat(b);
      if (!isNaN(numA) && !isNaN(numB)) {
        return numA - numB;
      }
      return String(a).localeCompare(String(b));
    });
  } else {
    uniqueValues.sort((a, b) => String(a).localeCompare(String(b)));
  }
  return uniqueValues;
};

const speedTiers = [
  { label: "Any Speed", value: "any" },
  { label: "50 Mbps+", value: "50" },
  { label: "100 Mbps+", value: "100" },
  { label: "250 Mbps+", value: "250" },
  { label: "500 Mbps+", value: "500" },
  { label: "1000 Mbps+", value: "1000" },
];

const dataLimitTiers = [
    { label: "Any Data Limit", value: "any" },
    { label: "Unlimited Data", value: "unlimited" },
    { label: "At least 100 GB", value: "100" },
    { label: "At least 250 GB", value: "250" },
    { label: "At least 500 GB", value: "500" },
];

function App() {
  const [offers, setOffers] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);

  const [sortBy, setSortBy] = useState('');
  const [filterConnectionTypes, setFilterConnectionTypes] = useState([]);
  const [filterProviderNames, setFilterProviderNames] = useState([]);
  const [filterContractTerms, setFilterContractTerms] = useState([]);
  const [filterMinDownloadSpeed, setFilterMinDownloadSpeed] = useState('any');
  const [filterDataLimit, setFilterDataLimit] = useState('any');

  const [currentSearchAddress, setCurrentSearchAddress] = useState(null);

  useEffect(() => {
    try {
      const storedAddress = localStorage.getItem(LOCAL_STORAGE_ADDRESS_KEY);
      if (storedAddress) {
        setCurrentSearchAddress(JSON.parse(storedAddress));
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
        if (parsedResults.filterMinDownloadSpeed) setFilterMinDownloadSpeed(parsedResults.filterMinDownloadSpeed);
        if (parsedResults.filterDataLimit) setFilterDataLimit(parsedResults.filterDataLimit);
      }
    } catch (e) {
      console.error("App.js: Error loading from localStorage on mount", e);
    }
  }, []);

  useEffect(() => {
    if (hasSearched || offers.length > 0) {
      try {
        const stateToStore = {
          offers, hasSearched, sortBy,
          filterConnectionTypes, filterProviderNames, filterContractTerms,
          filterMinDownloadSpeed, filterDataLimit,
        };
        localStorage.setItem(LOCAL_STORAGE_LAST_RESULTS_KEY, JSON.stringify(stateToStore));
      } catch (e) {
        console.error("App.js: Error saving state to localStorage", e);
      }
    }
  }, [offers, hasSearched, sortBy, filterConnectionTypes, filterProviderNames, filterContractTerms, filterMinDownloadSpeed, filterDataLimit]);

  const handleAddressSubmit = useCallback(async (addressDetailsFromForm) => {
    setIsLoading(true);
    setError(null);
    setHasSearched(true);
    setCurrentSearchAddress(addressDetailsFromForm);
    try {
      localStorage.setItem(LOCAL_STORAGE_ADDRESS_KEY, JSON.stringify(addressDetailsFromForm));
    } catch (e) {
      console.error("App.js: Error saving address to localStorage", e);
    }

    setSortBy('');
    setFilterConnectionTypes([]);
    setFilterProviderNames([]);
    setFilterContractTerms([]);
    setFilterMinDownloadSpeed('any');
    setFilterDataLimit('any');
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
        try { errorData = JSON.parse(responseText); }
        catch (e) { errorData = { message: `HTTP error! Status: ${response.status}. Response: ${responseText.substring(0, 200)}...` }; }
        throw new Error(errorData.message || `HTTP error! Status: ${response.status}`);
      }
      const data = await response.json();
      setOffers(data);
      
    } catch (err) {
      console.error("handleAddressSubmit: Error caught in try-catch block:", err);
      setError(err.message || 'Failed to fetch offers. Please try again.');
      
    } finally {
      setIsLoading(false);
    }
  }, []);

  const availableConnectionTypes = useMemo(() => getUniqueValues(offers, 'connectionType', false), [offers]);
  const availableProviderNames = useMemo(() => getUniqueValues(offers, 'providerName', false), [offers]);
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
    if (filterMinDownloadSpeed !== 'any') {
      const minSpeed = parseInt(filterMinDownloadSpeed, 10);
      processedOffers = processedOffers.filter(offer => offer.downloadSpeedMbps !== null && offer.downloadSpeedMbps >= minSpeed);
    }
    if (filterDataLimit !== 'any') {
      if (filterDataLimit === 'unlimited') {
        processedOffers = processedOffers.filter(offer => offer.dataLimitGb === null || offer.dataLimitGb === undefined || offer.dataLimitGb >= 10000);
      } else {
        const minData = parseInt(filterDataLimit, 10);
        processedOffers = processedOffers.filter(offer => offer.dataLimitGb !== null && offer.dataLimitGb >= minData);
      }
    }

    if (sortBy === 'price_asc') { processedOffers.sort((a, b) => (a.monthlyPriceEur ?? Infinity) - (b.monthlyPriceEur ?? Infinity)); }
    else if (sortBy === 'price_desc') { processedOffers.sort((a, b) => (b.monthlyPriceEur ?? -Infinity) - (a.monthlyPriceEur ?? -Infinity)); }
    else if (sortBy === 'speed_desc') { processedOffers.sort((a, b) => (b.downloadSpeedMbps ?? -Infinity) - (a.downloadSpeedMbps ?? -Infinity)); }
    else if (sortBy === 'speed_asc') { processedOffers.sort((a, b) => (a.downloadSpeedMbps ?? Infinity) - (b.downloadSpeedMbps ?? Infinity)); }
    else if (sortBy === 'contract_asc') { processedOffers.sort((a,b) => (a.contractTermMonths ?? Infinity) - (b.contractTermMonths ?? Infinity)); }
    return processedOffers;
  }, [offers, sortBy, filterConnectionTypes, filterProviderNames, filterContractTerms, filterMinDownloadSpeed, filterDataLimit]);

  const resetFiltersAndSort = () => {
    setSortBy('');
    setFilterConnectionTypes([]);
    setFilterProviderNames([]);
    setFilterContractTerms([]);
    setFilterMinDownloadSpeed('any');
    setFilterDataLimit('any');
  };



  const ComparisonPage = () => (
    <VStack spacing={8} align="stretch">
      <Heading as="h1" size="2xl" textAlign="center" color="teal.600" my={8}>
        Internet Provider Comparison
      </Heading>
      <AddressForm
        onSubmitAddress={handleAddressSubmit}
        isLoading={isLoading}
        currentAddress={currentSearchAddress}
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

            <FormControl>
              <FormLabel htmlFor="filter-min-speed" fontSize="sm" fontWeight="bold">Min. Download Speed:</FormLabel>
              <Select id="filter-min-speed" value={filterMinDownloadSpeed} onChange={(e) => setFilterMinDownloadSpeed(e.target.value)} size="sm" borderRadius="md">
                {speedTiers.map(tier => (
                  <option key={tier.value} value={tier.value}>{tier.label}</option>
                ))}
              </Select>
            </FormControl>

            <FormControl>
                <FormLabel fontSize="sm" fontWeight="bold">Data Limit:</FormLabel>
                <RadioGroup onChange={setFilterDataLimit} value={filterDataLimit} colorScheme="blue">
                    <Stack direction={{ base: "column", sm: "row" }} spacing={3} wrap="wrap">
                        {dataLimitTiers.map(tier => (
                            <Radio key={tier.value} value={tier.value} size="sm">
                                {tier.label}
                            </Radio>
                        ))}
                    </Stack>
                </RadioGroup>
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
              Reset All Filters & Sort
            </ChakraButton>
          </VStack>
        </Box>
      )}

      {isLoading && ( <Box textAlign="center" mt={10}> <Spinner size="xl" color="teal.500" /> <Heading as="h3" size="md" mt={4}>Fetching offers...please wait 10-30 seconds</Heading> </Box> )}
      {error && ( <Alert status="error" mt={6} variant="solid"> <AlertIcon /> {error} </Alert> )}
      
      {!isLoading && !error && hasSearched && (
        <Box mt={6}>
          <HStack justifyContent="space-between" alignItems="center" mb={4}>
            <Heading as="h2" size="lg">
              Comparison Results
              {displayedOffers.length > 0 && ` (${displayedOffers.length} offers found)`}
              {offers.length > 0 && displayedOffers.length !== offers.length && ` (from ${offers.length} total)`}
            </Heading>
            {/* Removed Share Button */}
            {/* {displayedOffers.length > 0 && (
              <ChakraButton colorScheme="green" onClick={handleShareResults} size="sm">
                Share These Results
              </ChakraButton>
            )} */}
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
        {/* Removed Share Route */}
        {/* <Route path="/share/:shareId" element={<SharedResultsPage />} /> */}
        <Route path="*" element={<Box textAlign="center" mt={20}><Heading>404 - Page Not Found</Heading><ChakraButton as={RouterLink} to="/" colorScheme="teal" mt={4}>Go Home</ChakraButton></Box>} />
      </Routes>

      {/* Removed Share Modal */}
      {/* <Modal isOpen={isShareModalOpen} onClose={onShareModalClose} isCentered> ... </Modal> */}
    </Box>
  );
}

export default App;