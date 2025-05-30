// src/OfferCard.js
import React from 'react';
import {
  Box,
  Heading,
  Text,
  Tag,
  VStack,
  HStack,
  Divider,
  Button,
  Badge, // For provider name or special tags
  List,
  ListItem,
  ListIcon
} from '@chakra-ui/react';
import { CheckCircleIcon, InfoOutlineIcon } from '@chakra-ui/icons'; // Example icons

function OfferCard({ offer }) {
  if (!offer) {
    return null; // Or some placeholder if an offer is unexpectedly null
  }

  // Helper to format price
  const formatPrice = (price) => {
    if (price === null || price === undefined) return 'N/A';
    return `€${price.toFixed(2)}`;
  };

  return (
    <Box
      borderWidth="1px"
      borderRadius="lg"
      p={5}
      boxShadow="md"
      width="100%"
      bg="white" // Background for the card
    >
      <VStack align="stretch" spacing={4}>
        {/* Provider and Product Name */}
        <HStack justifyContent="space-between">
          <Heading as="h3" size="md" color="teal.700">
            {offer.productName || 'Unnamed Product'}
          </Heading>
          <Badge colorScheme="green" fontSize="sm">{offer.providerName || 'Unknown Provider'}</Badge>
        </HStack>

        <Divider />

        {/* Core Details: Speed, Price, Contract */}
        <HStack justifyContent="space-around" spacing={4} wrap="wrap">
          <Box textAlign="center">
            <Text fontSize="sm" color="gray.500">Download Speed</Text>
            <Text fontSize="xl" fontWeight="bold">
              {offer.downloadSpeedMbps ? `${offer.downloadSpeedMbps} Mbps` : 'N/A'}
            </Text>
          </Box>
          <Box textAlign="center">
            <Text fontSize="sm" color="gray.500">Monthly Price</Text>
            <Text fontSize="xl" fontWeight="bold" color="green.600">
              {formatPrice(offer.monthlyPriceEur)}
            </Text>
            {offer.monthlyPriceEurAfter2Years && (
              <Text fontSize="xs" color="gray.500">
                (then {formatPrice(offer.monthlyPriceEurAfter2Years)}/month)
              </Text>
            )}
          </Box>
          <Box textAlign="center">
            <Text fontSize="sm" color="gray.500">Contract</Text>
            <Text fontSize="xl" fontWeight="bold">
              {offer.contractTermMonths ? `${offer.contractTermMonths} months` : 'N/A'}
            </Text>
          </Box>
        </HStack>

        {/* Connection Type and TV */}
        <HStack spacing={4}>
            {offer.connectionType && <Tag colorScheme="cyan">{offer.connectionType}</Tag>}
            {offer.tv && <Tag colorScheme="purple">TV: {offer.tv}</Tag>}
        </HStack>
        
        {/* Benefits / Discounts */}
        {(offer.benefits && offer.benefits !== "N/A") || offer.discount ? (
          <Box mt={2}>
            <Heading as="h4" size="sm" mb={1} color="gray.600">Benefits & Details:</Heading>
            <List spacing={1} fontSize="sm">
              {/* Displaying the main discount from normalized fields */}
              {offer.discount && offer.discountType && (
                <ListItem>
                  <ListIcon as={CheckCircleIcon} color="green.500" />
                  <strong>{offer.discountType}:</strong> {formatPrice(offer.discount)}
                </ListItem>
              )}
              {/* Displaying the assembled benefits string */}
              {offer.benefits && offer.benefits !== "N/A" && (
                <ListItem>
                   <ListIcon as={InfoOutlineIcon} color="blue.500" />
                   {offer.benefits}
                </ListItem>
              )}
            </List>
          </Box>
        ) : null}

        {/* Placeholder for a "details" or "to tariff" button */}
        <Button mt={4} colorScheme="blue" variant="outline" size="sm" alignSelf="flex-end">
          View Details
        </Button>
      </VStack>
    </Box>
  );
}

export default OfferCard;