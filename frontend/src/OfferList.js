// src/OfferList.js
import React from 'react';
import { SimpleGrid, Box, Text } from '@chakra-ui/react';
import OfferCard from './OfferCard'; // Import the OfferCard component

function OfferList({ offers }) {
  if (!offers || offers.length === 0) {
    return (
      <Box textAlign="center" mt={10}>
        <Text fontSize="lg" color="gray.600">No offers found for the selected criteria.</Text>
      </Box>
    );
  }

  return (
    // SimpleGrid is responsive by default.
    // minChildWidth makes columns that are at least 300px wide,
    // and it will wrap them as needed.
    // spacing adds gap between grid items.
    <SimpleGrid columns={{ sm: 1, md: 2, lg: 3 }} spacing={6} mt={6}>
      {offers.map((offer, index) => (
        // Using _provider_specific_id if available and unique enough,
        // otherwise fallback to index for the key.
        // A truly unique key from the data is always best.
        <OfferCard key={offer._provider_specific_id || `offer-${index}`} offer={offer} />
      ))}
    </SimpleGrid>
  );
}

export default OfferList;