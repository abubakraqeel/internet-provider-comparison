import os
import requests
from zeep import Client, Settings, xsd # xsd for creating complex types if needed
from zeep.transports import Transport
from zeep.helpers import serialize_object 
from lxml import etree # For parsing XML response, Zeep also uses lxml

# --- Credentials and Constants ---
WEBWUNDER_WSDL_URL = "https://webwunder.gendev7.check24.fun/endpunkte/soap/ws/getInternetOffers.wsdl"
WEBWUNDER_API_KEY = os.getenv("WEBWUNDER_API_KEY")
WEBWUNDER_SOAP_ENDPOINT = "https://webwunder.gendev7.check24.fun/endpunkte/soap/ws"
OFFER_NS = "http://webwunder.gendev7.check24.fun/offerservice" 


def _normalize_webwunder_offer_from_lxml(product_element): # product_element is an lxml <ns2:products>
    if product_element is None:
        return None

    # Namespace dictionary for lxml find calls within this function
    ns_map = {'sch': OFFER_NS}

    try:
        # product_element is an <ns2:products> element.
        # Its children <ns2:productId>, <ns2:providerName>, <ns2:productInfo> are in the same namespace.
        
        product_id_str = product_element.findtext('sch:productId', namespaces=ns_map)
        api_provider_name_field = product_element.findtext('sch:providerName', namespaces=ns_map) or "WebWunder Product"
        
        product_info_element = product_element.find('sch:productInfo', namespaces=ns_map)

        if product_info_element is None:
            print(f"WebWunder XML Norm: sch:productInfo element not found for productId {product_id_str}")
            return None

        provider_specific_id = str(product_id_str) if product_id_str else f"unknown_ww_id_{time.time()}" # Add timestamp for uniqueness
        
        speed_str = product_info_element.findtext('sch:speed', namespaces=ns_map)
        conn_type_str = product_info_element.findtext('sch:connectionType', namespaces=ns_map)
        product_name = f"{api_provider_name_field}" # API providerName is already descriptive enough

        download_speed_mbps = int(speed_str) if speed_str and speed_str.isdigit() else None
        upload_speed_mbps = None

        monthly_cost_cents_str = product_info_element.findtext('sch:monthlyCostInCent', namespaces=ns_map)
        monthly_price_eur = int(monthly_cost_cents_str) / 100.0 if monthly_cost_cents_str and monthly_cost_cents_str.isdigit() else None

        monthly_cost_25th_cents_str = product_info_element.findtext('sch:monthlyCostInCentFrom25thMonth', namespaces=ns_map)
        monthly_price_eur_after_2_years = int(monthly_cost_25th_cents_str) / 100.0 if monthly_cost_25th_cents_str and monthly_cost_25th_cents_str.isdigit() else None
        if monthly_price_eur_after_2_years == monthly_price_eur: # Avoid redundancy
            monthly_price_eur_after_2_years = None 
        
        contract_term_months_str = product_info_element.findtext('sch:contractDurationInMonths', namespaces=ns_map)
        contract_term_months = int(contract_term_months_str) if contract_term_months_str and contract_term_months_str.isdigit() else None
        
        connection_type = conn_type_str

        benefits_list = []
        tv_package = None 
        
        discount_value_eur = None
        discount_type_str = None
        one_time_cost_eur = 0.00 

        voucher_element = product_info_element.find('sch:voucher', namespaces=ns_map)
        if voucher_element is not None:
            xsi_type = voucher_element.get('{http://www.w3.org/2001/XMLSchema-instance}type') 
            
            # The actual tag name of voucher_element might also indicate its type
            # e.g. if it's <sch:percentageVoucher> or <sch:absoluteVoucher>
            actual_voucher_tag = etree.QName(voucher_element.tag).localname

            if (xsi_type and "absoluteVoucher" in xsi_type) or actual_voucher_tag == "absoluteVoucher":
                discount_type_str = "Absolute Voucher"
                disc_cent_str = voucher_element.findtext('sch:discountInCent', namespaces=ns_map)
                min_order_str = voucher_element.findtext('sch:minOrderValueInCent', namespaces=ns_map)
                if disc_cent_str and disc_cent_str.isdigit():
                    discount_value_eur = int(disc_cent_str) / 100.0
                    min_order_val = int(min_order_str) / 100.0 if min_order_str and min_order_str.isdigit() else 0
                    benefits_list.append(f"Discount: €{discount_value_eur:.2f} (min. order value: €{min_order_val:.2f})")
                    # one_time_cost_eur -= discount_value_eur # Apply as cashback/reduction - hold for now
            elif (xsi_type and "percentageVoucher" in xsi_type) or actual_voucher_tag == "percentageVoucher":
                discount_type_str = "Percentage Voucher"
                perc_str = voucher_element.findtext('sch:percentage', namespaces=ns_map)
                max_disc_cent_str = voucher_element.findtext('sch:maxDiscountInCent', namespaces=ns_map)
                if perc_str and perc_str.isdigit() and max_disc_cent_str and max_disc_cent_str.isdigit():
                    perc_val = int(perc_str)
                    max_disc_eur = int(max_disc_cent_str) / 100.0
                    benefits_list.append(f"Discount: {perc_val}% (up to €{max_disc_eur:.2f})")
            # else:
                # print(f"Voucher type not recognized: xsi:type='{xsi_type}', tag='{actual_voucher_tag}'")


        # For oneTimeCostEur, if there's a discount, it likely reduces this.
        # The WSDL doesn't show a setup fee, so vouchers act like pure credit/cashback.
        if discount_value_eur is not None and discount_type_str == "Absolute Voucher":
            one_time_cost_eur -= discount_value_eur # Makes it negative if pure cashback

        installation_service_included = None 
        age_restriction_max = None
        data_limit_gb = None

        normalized_offer = {
            "providerName": "WebWunder",
            "productName": product_name,
            "downloadSpeedMbps": download_speed_mbps,
            "uploadSpeedMbps": upload_speed_mbps,
            "monthlyPriceEur": monthly_price_eur,
            "monthlyPriceEurAfter2Years": monthly_price_eur_after_2_years,
            "contractTermMonths": contract_term_months,
            "connectionType": connection_type,
            "benefits": ", ".join(benefits_list) if benefits_list else "N/A",
            "tv": tv_package, # Populated if found
            "discount": discount_value_eur, # Value of discount in EUR
            "discountType": discount_type_str, # Type of discount
            "installationServiceIncluded": installation_service_included, # Populated if found
            "ageRestrictionMax": age_restriction_max, # Populated if found
            "dataLimitGb": data_limit_gb, # Populated if found
            "_provider_specific_id": provider_specific_id,
        }
        return normalized_offer
    except Exception as e:
        print(f"WebWunder XML Norm Error: {e} for product ID {product_element.findtext('sch:productId', namespaces=ns_map if 'ns_map' in locals() else None)}")
        import traceback
        traceback.print_exc()
        return None

def get_webwunder_offers(address_details):
    if not WEBWUNDER_API_KEY:
        print("WebWunder API Key (WEBWUNDER_API_KEY) is not configured.")
        return []

    all_normalized_offers_accumulated = []
    
    connection_types_to_query = ["DSL", "CABLE", "FIBER", "MOBILE"]
    # For debugging, start with one:
    # connection_types_to_query = ["DSL"] 

    for conn_type in connection_types_to_query:
        print(f"\nWebWunder: Querying for connection type: {conn_type}")
        
        input_payload_dict = {
            'installation': True,
            'connectionEnum': conn_type,
            'address': {
                'street': address_details.get("strasse"),
                'houseNumber': address_details.get("hausnummer"),
                'city': address_details.get("stadt"),
                'plz': address_details.get("postleitzahl"),
                'countryCode': address_details.get("land", "DE")
            }
        }

        gs_namespace_uri_for_payload = OFFER_NS # Use the same URI for gs: prefix in payload
        
        input_xml_parts = [
            f"<gs:installation xmlns:gs=\"{gs_namespace_uri_for_payload}\">{str(input_payload_dict['installation']).lower()}</gs:installation>",
            f"<gs:connectionEnum xmlns:gs=\"{gs_namespace_uri_for_payload}\">{input_payload_dict['connectionEnum']}</gs:connectionEnum>"
        ]
        # Address parts should also be under gs namespace
        input_xml_parts.append(f"<gs:address xmlns:gs=\"{gs_namespace_uri_for_payload}\">")
        for key, value in input_payload_dict['address'].items():
            input_xml_parts.append(f"<gs:{key}>{value}</gs:{key}>")
        input_xml_parts.append("</gs:address>")
        input_content_xml = "".join(input_xml_parts)

        # The legacyGetInternetOffers and input elements are also in the gs_namespace
        soap_body_content = f"""
        <gs:legacyGetInternetOffers xmlns:gs="{gs_namespace_uri_for_payload}">
            <gs:input>
                {input_content_xml}
            </gs:input>
        </gs:legacyGetInternetOffers>
        """

        soap_envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
           <soapenv:Header/>
           <soapenv:Body>
              {soap_body_content}
           </soapenv:Body>
        </soapenv:Envelope>
        """
        
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'X-Api-Key': WEBWUNDER_API_KEY,
            'SOAPAction': '' 
        }

        try:
            print(f"WebWunder ({conn_type}): Sending manual SOAP request to {WEBWUNDER_SOAP_ENDPOINT}")
            # print(f"SOAP Payload being sent:\n{soap_envelope}\n-----------------------------------")

            response = requests.post(
                WEBWUNDER_SOAP_ENDPOINT,
                data=soap_envelope.encode('utf-8'),
                headers=headers,
                timeout=30
            )
            
            raw_xml_response = "COULD_NOT_DECODE_RESPONSE"
            try:
                raw_xml_response = response.content.decode('utf-8')
            except UnicodeDecodeError:
                try: raw_xml_response = response.content.decode('latin-1')
                except Exception: pass
            
            if response.status_code != 200: # Print raw for non-200 before raising
                print(f"WebWunder ({conn_type}): Non-200 Status {response.status_code}. RAW XML Response:")
                print(raw_xml_response)
                print("--------------------------------------")
            response.raise_for_status() 
            
            # If status is 200, print for debugging successful response content
            if conn_type == connection_types_to_query[0]: # Print only for the first type to avoid too much log
                print(f"WebWunder ({conn_type}): RAW XML Response Content (Status {response.status_code}):")
                print(raw_xml_response)
                print("--------------------------------------")


            xml_namespaces_for_parsing = {
                'soapenv': 'http://schemas.xmlsoap.org/soap/envelope/',
                'sch': OFFER_NS 
            }
            # recover=True can help with slightly malformed XML from server
            parser = etree.XMLParser(remove_blank_text=True, recover=True) 
            tree = etree.fromstring(response.content, parser=parser)

            fault_element = tree.find('.//soapenv:Fault', namespaces=xml_namespaces_for_parsing)
            if fault_element is not None:
                faultstring_element = fault_element.find('faultstring') # faultstring is usually not namespaced
                faultstring = faultstring_element.text if faultstring_element is not None else "Unknown SOAP fault"
                print(f"WebWunder ({conn_type}): SOAP Fault found in response: {faultstring}")
                continue

            body_element = tree.find('.//soapenv:Body', namespaces=xml_namespaces_for_parsing)
            product_elements_from_xpath = []
            if body_element is not None:
                # The <Output> element in response: <Output xmlns:ns2="OFFER_NS">
                # It is NOT prefixed itself. Its children <ns2:products> ARE prefixed.
                output_el = body_element.find('./Output') # Find Output without prefix
                if output_el is None: # Fallback if server sends it namespaced
                    output_el = body_element.find('./sch:Output', namespaces=xml_namespaces_for_parsing)

                if output_el is not None:
                    # Find 'sch:products' children of 'output_el'
                    product_elements_from_xpath = output_el.findall('./sch:products', namespaces=xml_namespaces_for_parsing)
                else:
                    print(f"WebWunder ({conn_type}): <Output> element not found in SOAP Body.")
            else:
                print(f"WebWunder ({conn_type}): <soapenv:Body> element not found.")
            
            current_type_offers_count = 0
            if product_elements_from_xpath:
                print(f"WebWunder ({conn_type}): Found {len(product_elements_from_xpath)} 'sch:products' elements.")
                for product_el in product_elements_from_xpath:
                    normalized = _normalize_webwunder_offer_from_lxml(product_el)
                    if normalized:
                        all_normalized_offers_accumulated.append(normalized)
                        current_type_offers_count +=1
            else:
                 print(f"WebWunder ({conn_type}): No 'sch:products' elements found.")
            
            print(f"WebWunder ({conn_type}): Processed {current_type_offers_count} offers for this type.")

        # ... (keep existing except blocks) ...
        except requests.exceptions.HTTPError as e: # Catch HTTP errors
            print(f"WebWunder ({conn_type}): HTTP error: {e.response.status_code if e.response else 'N/A'}")
            # Raw XML response might have been printed above if status_code was not 200 initially
            if e.response and e.response.text and response.status_code == 200 : # Only print if not already printed
                 print(f"Error Response body for HTTPError: {e.response.text[:700]}...")
        except requests.exceptions.Timeout:
            print(f"WebWunder ({conn_type}): Timeout during manual SOAP request.")
        except requests.exceptions.RequestException as e:
            print(f"WebWunder ({conn_type}): Request error: {e}")
        except etree.XMLSyntaxError as e:
            print(f"WebWunder ({conn_type}): XMLSyntaxError parsing SOAP response: {e}")
        except Exception as e:
            print(f"WebWunder ({conn_type}): An unexpected error occurred: {e}")
            import traceback
            traceback.print_exc()
        
    print(f"\nWebWunder (Overall): Successfully processed and normalized {len(all_normalized_offers_accumulated)} total offers from all queried connection types.")
    return all_normalized_offers_accumulated

# ... (if __name__ == '__main__': block, ensure it calls the new get_webwunder_offers)

# --- Example for direct testing (optional) ---
if __name__ == '__main__':
    # For direct script execution, you might need to load .env explicitly
    # if your Flask app usually handles it.
    # Install python-dotenv first: pip install python-dotenv
    try:
        from dotenv import load_dotenv
        print("Attempting to load .env file...")
        if load_dotenv():
            print(".env file loaded successfully.")
        else:
            print(".env file not found or failed to load. Ensure environment variables are set.")
    except ImportError:
        print("python-dotenv not installed. Ensure environment variables (e.g., WEBWUNDER_API_KEY) are set manually.")

    # Reload API_KEY after dotenv load, as it's defined at module level
    WEBWUNDER_API_KEY = os.getenv("WEBWUNDER_API_KEY")

    if not WEBWUNDER_API_KEY:
        print("\nERROR: WEBWUNDER_API_KEY is not set in your environment variables or .env file.")
        print("Please set it before running this test.")
    else:
        print(f"\nUsing WEBWUNDER_API_KEY: {WEBWUNDER_API_KEY[-4:]}") # Print last 4 chars for verification

        # Sample address details (matching the structure expected by get_webwunder_offers)
        # This function expects keys like "strasse", "hausnummer", etc.
        sample_address = {
            "strasse": "Musterstraße",  # German key as per your address_details convention
            "hausnummer": "123",
            "postleitzahl": "10115",    # Example PLZ (Berlin)
            "stadt": "Berlin",
            "land": "DE"                # WSDL supports DE, AT, CH
        }
        # Test with an address that is likely to yield results.
        # You might need to try different valid addresses.

        print(f"\nTesting get_webwunder_offers with address: {sample_address}")
        
        # To see the raw SOAP request/response with zeep, you can enable history plugin (optional advanced debug)
        # from zeep.plugins import HistoryPlugin
        # history = HistoryPlugin()
        # client = Client(WEBWUNDER_WSDL_URL, transport=transport, plugins=[history])
        # After the call:
        # from lxml import etree
        # print(etree.tostring(history.last_sent['envelope'], encoding="unicode", pretty_print=True))
        # print(etree.tostring(history.last_received['envelope'], encoding="unicode", pretty_print=True))

        offers = get_webwunder_offers(sample_address)
        
        import json
        if offers:
            print(f"\n--- Found {len(offers)} WebWunder Offers ---")
            # Pretty print the JSON list of offer dictionaries
            print(json.dumps(offers, indent=2, ensure_ascii=False)) # ensure_ascii=False for German characters
        elif offers == []: # Explicitly check for empty list vs None (which might indicate an error before list creation)
             print("\n--- No WebWunder offers were found for this address (list is empty). ---")
        else: # offers might be None if a critical error occurred before list initialization
            print("\n--- No WebWunder offers returned, or a critical error occurred during fetching. ---")