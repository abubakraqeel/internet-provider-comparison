# app/services/webwunder_client.py
import os
import requests
from lxml import etree # Using lxml directly for robust parsing
import time # For unique ID fallback

# --- Credentials and Constants ---
WEBWUNDER_API_KEY = os.getenv("WEBWUNDER_API_KEY")
WEBWUNDER_SOAP_ENDPOINT = "https://webwunder.gendev7.check24.fun/endpunkte/soap/ws" # WSDL URL not needed for direct POST
OFFER_NS = "http://webwunder.gendev7.check24.fun/offerservice"

def _normalize_webwunder_offer_from_lxml(product_element):
    if product_element is None:
        return None
    ns_map = {'sch': OFFER_NS}
    try:
        product_id_str = product_element.findtext('sch:productId', namespaces=ns_map)
        api_provider_name_field = product_element.findtext('sch:providerName', namespaces=ns_map) or "WebWunder"
        product_info_element = product_element.find('sch:productInfo', namespaces=ns_map)

        if product_info_element is None:
            # print(f"WebWunder Norm: productInfo missing for {product_id_str}")
            return None

        provider_specific_id = str(product_id_str) if product_id_str else f"ww_unknown_{int(time.time()*1000)}"
        
        # Use .get('name', api_provider_name_field) to ensure product name uses the specific name if available
        product_name = product_info_element.get('name', api_provider_name_field) 
        if not product_name or product_name == api_provider_name_field: # If name is same as provider or missing
             # Construct a more descriptive name if possible
            speed_for_name = product_info_element.findtext('sch:speed', namespaces=ns_map)
            conn_type_for_name = product_info_element.findtext('sch:connectionType', namespaces=ns_map)
            if speed_for_name and conn_type_for_name:
                product_name = f"{api_provider_name_field} {conn_type_for_name} {speed_for_name}"
            elif speed_for_name:
                 product_name = f"{api_provider_name_field} {speed_for_name}"
            else: # Fallback if still not descriptive
                 product_name = f"{api_provider_name_field} Offer {provider_specific_id.split('_')[-1]}"


        speed_str = product_info_element.findtext('sch:speed', namespaces=ns_map)
        conn_type_str = product_info_element.findtext('sch:connectionType', namespaces=ns_map)
        download_speed_mbps = int(speed_str) if speed_str and speed_str.isdigit() else None
        
        monthly_cost_cents_str = product_info_element.findtext('sch:monthlyCostInCent', namespaces=ns_map)
        monthly_price_eur = int(monthly_cost_cents_str) / 100.0 if monthly_cost_cents_str and monthly_cost_cents_str.isdigit() else None

        monthly_cost_25th_cents_str = product_info_element.findtext('sch:monthlyCostInCentFrom25thMonth', namespaces=ns_map)
        monthly_price_eur_after_2_years = int(monthly_cost_25th_cents_str) / 100.0 if monthly_cost_25th_cents_str and monthly_cost_25th_cents_str.isdigit() else None
        if monthly_price_eur_after_2_years == monthly_price_eur:
            monthly_price_eur_after_2_years = None
        
        contract_term_months_str = product_info_element.findtext('sch:contractDurationInMonths', namespaces=ns_map)
        contract_term_months = int(contract_term_months_str) if contract_term_months_str and contract_term_months_str.isdigit() else None
        
        benefits_list = []
        discount_value_eur = None
        discount_type_str = None
        
        voucher_element = product_info_element.find('sch:voucher', namespaces=ns_map)
        if voucher_element is not None:
            xsi_type = voucher_element.get('{http://www.w3.org/2001/XMLSchema-instance}type', '')
            actual_voucher_tag = etree.QName(voucher_element.tag).localname

            if "absoluteVoucher" in xsi_type or actual_voucher_tag == "absoluteVoucher":
                discount_type_str = "Absolute Voucher"
                # ... (rest of voucher parsing as before) ...
            elif "percentageVoucher" in xsi_type or actual_voucher_tag == "percentageVoucher":
                discount_type_str = "Percentage Voucher"
                # ... (rest of voucher parsing as before) ...

        normalized_offer = {
            "providerName": "WebWunder", "productName": product_name,
            "downloadSpeedMbps": download_speed_mbps, "uploadSpeedMbps": None,
            "monthlyPriceEur": monthly_price_eur, "monthlyPriceEurAfter2Years": monthly_price_eur_after_2_years,
            "contractTermMonths": contract_term_months, "connectionType": conn_type_str.title() if conn_type_str and conn_type_str != "DSL" else conn_type_str,
            "benefits": ", ".join(benefits_list) if benefits_list else "N/A", "tv": None,
            "discount": discount_value_eur, "discountType": discount_type_str,
            "installationServiceIncluded": None, "ageRestrictionMax": None, "dataLimitGb": None,
            "_provider_specific_id": provider_specific_id,
        }
        return normalized_offer
    except Exception as e:
        print(f"WebWunder Norm Error: {e} for product ID {product_element.findtext('sch:productId', namespaces=ns_map if 'ns_map' in locals() else None)}")
        return None

def fetch_webwunder_offers(address_details, connection_type_param="DSL", installation_param=True): # Renamed
    if not WEBWUNDER_API_KEY:
        print(f"WebWunder Client ERROR ({connection_type_param}): API Key not configured.")
        return []

    # Address details mapping for payload
    addr_payload = {
        'street': address_details.get("strasse"), 'houseNumber': address_details.get("hausnummer"),
        'city': address_details.get("stadt"), 'plz': address_details.get("postleitzahl"),
        'countryCode': address_details.get("land", "DE")
    }
    if not all(addr_payload.values()): # Basic check
        print(f"WebWunder Client WARNING ({connection_type_param}): Missing address components. Details: {address_details}")
        return []
        
    gs_ns = OFFER_NS
    input_xml_parts = [
        f"<gs:installation xmlns:gs=\"{gs_ns}\">{str(installation_param).lower()}</gs:installation>",
        f"<gs:connectionEnum xmlns:gs=\"{gs_ns}\">{connection_type_param}</gs:connectionEnum>",
        f"<gs:address xmlns:gs=\"{gs_ns}\">"
    ]
    for key, value in addr_payload.items():
        input_xml_parts.append(f"<gs:{key}>{value}</gs:{key}>")
    input_xml_parts.append("</gs:address>")
    input_content_xml = "".join(input_xml_parts)

    soap_body_content = f"<gs:legacyGetInternetOffers xmlns:gs=\"{gs_ns}\"><gs:input>{input_content_xml}</gs:input></gs:legacyGetInternetOffers>"
    soap_envelope = f"<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\"><soapenv:Header/><soapenv:Body>{soap_body_content}</soapenv:Body></soapenv:Envelope>"
    
    headers = {'Content-Type': 'text/xml; charset=utf-8', 'X-Api-Key': WEBWUNDER_API_KEY, 'SOAPAction': ''}
    normalized_offers_for_type = []

    try:
        # print(f"WebWunder Client ({connection_type_param}): Sending SOAP request...")
        response = requests.post(WEBWUNDER_SOAP_ENDPOINT, data=soap_envelope.encode('utf-8'), headers=headers, timeout=25)
        # print(f"WebWunder Client ({connection_type_param}): API response status: {response.status_code}")
        
        raw_xml_response = "COULD_NOT_DECODE_RESPONSE"
        try: raw_xml_response = response.content.decode('utf-8')
        except: pass
            
        if response.status_code != 200:
            print(f"WebWunder Client ({connection_type_param}): Non-200 Status {response.status_code}. Raw Resp: {raw_xml_response[:500]}")
        response.raise_for_status()
        
        parser = etree.XMLParser(remove_blank_text=True, recover=True)
        tree = etree.fromstring(response.content, parser=parser)
        xml_namespaces = {'soapenv': 'http://schemas.xmlsoap.org/soap/envelope/', 'sch': OFFER_NS}

        fault_element = tree.find('.//soapenv:Fault', namespaces=xml_namespaces)
        if fault_element is not None:
            faultstring = fault_element.findtext('faultstring', default="Unknown SOAP fault")
            print(f"WebWunder Client ({connection_type_param}) SOAP FAULT: {faultstring}")
            return []

        output_el = tree.find('.//soapenv:Body/sch:Output', namespaces=xml_namespaces) # More specific path
        if output_el is None: # Try without sch prefix if server response varies
             output_el = tree.find('.//soapenv:Body/Output', namespaces=xml_namespaces)

        if output_el is not None:
            product_elements = output_el.findall('./sch:products', namespaces=xml_namespaces)
            # print(f"WebWunder Client ({connection_type_param}): Found {len(product_elements)} product elements.")
            for product_el in product_elements:
                normalized = _normalize_webwunder_offer_from_lxml(product_el)
                if normalized:
                    normalized_offers_for_type.append(normalized)
        else:
            print(f"WebWunder Client ({connection_type_param}) WARNING: <Output> element not found in SOAP Body. Raw: {raw_xml_response[:500]}")

    except requests.exceptions.Timeout:
        print(f"WebWunder Client ({connection_type_param}) ERROR: Timeout during SOAP request.")
    except requests.exceptions.HTTPError as http_err:
        print(f"WebWunder Client ({connection_type_param}) HTTP ERROR: {http_err.response.status_code if http_err.response else 'N/A'}")
    except requests.exceptions.RequestException as req_err:
        print(f"WebWunder Client ({connection_type_param}) REQUEST EXCEPTION: {req_err}")
    except etree.XMLSyntaxError as xml_err:
        print(f"WebWunder Client ({connection_type_param}) XML PARSE ERROR: {xml_err}. Raw Resp: {raw_xml_response[:500]}")
    except Exception as e:
        print(f"WebWunder Client ({connection_type_param}) UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()

    print(f"WebWunder Client: Processed {len(normalized_offers_for_type)} offers for type {connection_type_param}.")
    return normalized_offers_for_type

# ... (if __name__ == '__main__': block needs to be updated to call fetch_webwunder_offers for each type)
# Note: The main routes.py will handle iterating through connection types for WebWunder.