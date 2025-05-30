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
  Badge,
  List,
  ListItem,
  ListIcon,
  Flex,
  Tooltip
} from '@chakra-ui/react';
import { CheckCircleIcon, InfoOutlineIcon, WarningTwoIcon, LockIcon, DownloadIcon, CalendarIcon, SmallCloseIcon } from '@chakra-ui/icons'; // Added SmallCloseIcon for "not included"

function OfferCard({ offer }) {
  if (!offer) {
    return null;
  }

  const formatPrice = (price) => {
    if (price === null || price === undefined) return 'N/A';
    return `€${price.toFixed(2)}`;
  };

  const detailItems = [];

  // 1. Discount
  if (offer.discount && offer.discountType) {
    let discountText = `${offer.discountType}: ${formatPrice(offer.discount)}`;
    if (offer.discountType.toLowerCase().includes("percentage") && offer.benefits && offer.benefits.includes("max total")) {
        const maxTotalMatch = offer.benefits.match(/max total €([\d.]+)/);
        const percDetailsMatch = offer.benefits.match(/(\d+)% monthly discount for (\d+) months/);
        let percInfo = "";
        if (percDetailsMatch) {
            percInfo = ` (${percDetailsMatch[1]}% for ${percDetailsMatch[2]} mths)`;
        }
        if (maxTotalMatch) {
            discountText = `${offer.discountType.replace(' (Monthly)','')}${percInfo}, max total: ${formatPrice(parseFloat(maxTotalMatch[1]))}`;
        }
    } else if (offer.discountType.toLowerCase().includes("one-time") && offer.benefits && offer.benefits.includes("min. order")){
        const minOrderMatch = offer.benefits.match(/min\. order €([\d.]+)/);
        if (minOrderMatch) {
            discountText += ` (min. order value: ${formatPrice(parseFloat(minOrderMatch[1]))})`;
        }
    }
    detailItems.push({ text: discountText, icon: CheckCircleIcon, color: 'green.500' });
  }

  // 2. TV Package - MODIFIED
  if (offer.tv && typeof offer.tv === 'string' && offer.tv.trim() !== "" && offer.tv.toLowerCase() !== "none") {
    detailItems.push({ text: `TV Package: ${offer.tv}`, icon: InfoOutlineIcon, color: 'purple.500' });
  }
  
  // 3. Data Limit
  if (offer.dataLimitGb !== null && offer.dataLimitGb !== undefined) {
    let dataLimitText = `Data Limit: ${offer.dataLimitGb} GB/month`;
    if (offer.benefits && offer.benefits.toLowerCase().includes(`throttled after ${offer.dataLimitGb}gb`)) {
      dataLimitText += " (speed throttled afterwards)";
    }
    detailItems.push({ text: dataLimitText, icon: DownloadIcon, color: 'blue.500' });
  }
  
  // 4. Age Restriction
  if (offer.ageRestrictionMax !== null && offer.ageRestrictionMax !== undefined) {
    detailItems.push({ text: `Age Restriction: Up to ${offer.ageRestrictionMax -1} years (under ${offer.ageRestrictionMax})`, icon: LockIcon, color: 'orange.500' });
  }

  // 5. Installation Service
  if (offer.installationServiceIncluded === true) {
    detailItems.push({ text: "Installation service included", icon: CheckCircleIcon, color: 'green.500' });
  } else if (offer.installationServiceIncluded === false) {
    // Only add a note if there's a specific fee mentioned or if we want to state "not included"
    let installationNote = null;
    if (offer.oneTimeCostEur > 0 && offer.benefits && offer.benefits.toLowerCase().includes("installation fee:")) {
        installationNote = `Installation Fee: ${formatPrice(offer.oneTimeCostEur)}`;
        detailItems.push({ text: installationNote, icon: WarningTwoIcon, color: 'red.500' });
    }
    // else if (offer.installationServiceIncluded === false) { 
    //    detailItems.push({ text: "Installation not included", icon: SmallCloseIcon, color: 'gray.500' }); // Optional to state "not included"
    // }
  }


  // 6. Other benefits from the generic 'benefits' string (if not already covered)
  const alreadyCoveredKeywordsInBenefits = [
      "tv package:", // More specific now that we handle offer.tv directly
      "data limit:", "age restriction:", "installation service included", "installation fee:",
      offer.discountType?.toLowerCase().replace(' (monthly)','').replace(' voucher',''),
      "max total €", "min. order €", "throttled after"
  ];

  if (offer.benefits && offer.benefits.toLowerCase() !== "n/a") {
    const generalBenefitParts = offer.benefits.split(',')
      .map(b => b.trim())
      .filter(b => {
        if (!b) return false;
        return !alreadyCoveredKeywordsInBenefits.some(keyword => keyword && b.toLowerCase().includes(keyword.toLowerCase()));
      });
    
    generalBenefitParts.forEach(b => {
      if (b) {
        detailItems.push({ text: b, icon: InfoOutlineIcon, color: 'gray.600' });
      }
    });
  }


  return (
    <Box
      borderWidth="1px"
      borderRadius="lg"
      p={5}
      boxShadow="lg"
      width="100%"
      bg="white"
      transition="all 0.2s"
      _hover={{ boxShadow: "xl", transform: "translateY(-2px)" }}
    >
      <VStack align="stretch" spacing={3}>
        <Flex justifyContent="space-between" alignItems="flex-start">
          <Heading as="h3" size="md" color="blue.700" noOfLines={2} flex="1" mr={2}>
            {offer.productName || 'Unnamed Product'}
          </Heading>
          <Badge colorScheme="gray" variant="outline" fontSize="xs" ml={2} whiteSpace="nowrap" mt={1}>
            {offer.providerName || 'Provider'}
          </Badge>
        </Flex>

        <Divider />

        <HStack justifyContent="space-around" spacing={{base: 2, md: 4}} wrap="wrap" py={2}>
          <Box textAlign="center" minW="100px">
            <Text fontSize="xs" color="gray.500" casing="uppercase">Download</Text>
            <Text fontSize="lg" fontWeight="bold">
              {offer.downloadSpeedMbps ? `${offer.downloadSpeedMbps} Mbps` : 'N/A'}
            </Text>
          </Box>
          <Box textAlign="center" minW="100px">
            <Text fontSize="xs" color="gray.500" casing="uppercase">Price / month</Text>
            <Text fontSize="lg" fontWeight="bold" color="green.600">
              {formatPrice(offer.monthlyPriceEur)}
            </Text>
            {offer.monthlyPriceEurAfter2Years && offer.monthlyPriceEurAfter2Years !== offer.monthlyPriceEur && (
              <Tooltip label="Price after initial term" placement="bottom" hasArrow bg="gray.700" color="white">
                <Text fontSize="2xs" color="gray.500" mt={0.5} cursor="default">
                  (then {formatPrice(offer.monthlyPriceEurAfter2Years)})
                </Text>
              </Tooltip>
            )}
          </Box>
          <Box textAlign="center" minW="100px">
            <Text fontSize="xs" color="gray.500" casing="uppercase">Contract</Text>
            <Text fontSize="lg" fontWeight="bold">
              {offer.contractTermMonths ? `${offer.contractTermMonths} mths` : 'N/A'}
            </Text>
          </Box>
        </HStack>
        
        {/* Display Connection Type as a Tag if it exists */}
        {offer.connectionType && (
            <>
                <Divider my={1}/>
                <HStack spacing={2} wrap="wrap" justifyContent={{base: "center", md: "flex-start"}}>
                    <Tag size="sm" colorScheme="blue" variant="subtle">{offer.connectionType}</Tag>
                </HStack>
            </>
        )}
        
        {detailItems.length > 0 ? (
          <Box pt={2}>
            <Heading as="h4" size="xs" mb={2} color="gray.700" casing="uppercase">
              Key Details & Benefits:
            </Heading>
            <List spacing={1} fontSize="sm">
              {detailItems.map((item, index) => (
                <ListItem key={index} display="flex" alignItems="center">
                  <ListIcon as={item.icon} color={item.color} />
                  <Text as="span" ml={1} dangerouslySetInnerHTML={{ 
                      __html: item.text.replace(/^([^:]+:)/, '<strong>$1</strong>') 
                  }} />
                </ListItem>
              ))}
            </List>
          </Box>
        ) : null}

        <Button mt={3} colorScheme="blue" variant="solid" size="sm" alignSelf="center" w={{base: "80%", md: "60%"}}>
            View Offer
        </Button>
      </VStack>
    </Box>
  );
}

export default OfferCard;