# Internet Provider Comparison Application

This full-stack web application allows users to compare internet offers from various providers by entering their address details. It is designed to provide a smooth user experience even when dealing with potentially unreliable third-party APIs.

**Deployed Application Link:** [Your Deployed Application URL Here - e.g., on PythonAnywhere]
**Video Demo (if applicable):** [Link to Video Demo Here]

## Challenge Overview

The core challenge was to build an application that aggregates internet offers from five different providers, each with a unique and potentially unreliable API. Key requirements included robust error handling, useful sorting/filtering, a shareable link feature for results, and secure credential management.

## Core Features

*   **Address-Based Offer Search:** Users can input their address to fetch relevant internet offers.
*   **Multi-Provider Comparison:** Aggregates offers from five distinct internet providers.
*   **Robust API Integration:** Designed to handle API failures and delays gracefully, ensuring users still see results from responsive providers.
*   **Data Normalization:** Transforms diverse API responses into a consistent JSON structure for a unified display.
*   **Sorting & Filtering:** Users can sort offers (by price, speed, etc.) and filter them (by provider, connection type, contract term).
*   **Shareable Results Links:** Users can generate a unique link to share their current search results with others. These links persist the displayed offers.
*   **Responsive UI:** Built with Chakra UI for a clean and accessible user interface.
*   **Client-Side State Persistence:**
    *   Remembers the user's last entered address details.
    *   Remembers the last fetched offers and applied filters/sort order, restoring the view on page reload.

## Technical Stack

*   **Backend:** Python (Flask)
*   **Frontend:** React.js, JavaScript, HTML, CSS
*   **UI Library:** Chakra UI
*   **Database:** MySQL (for the share link feature)
*   **API Interaction:** `requests` library (Python), `zeep` (for SOAP), `lxml` (for XML parsing)
*   **Concurrency:** `ThreadPoolExecutor` for concurrent API calls.

## Backend Implementation

The Flask backend serves as the central orchestrator for fetching, processing, and serving internet offer data.

### 1. API Integration & Fault Tolerance

A significant challenge was integrating with five diverse and potentially unreliable provider APIs:

*   **WebWunder:** SOAP web service (XML).
*   **ByteMe:** CSV data over HTTP (with deduplication logic).
*   **Ping Perfect:** REST/JSON with custom HMAC-SHA256 request signing.
*   **VerbynDich:** Non-standard API requiring string parsing from a description field and pagination.
*   **Servus Speed:** REST/JSON with Basic Auth, requiring a two-step product fetch.

**Fault Handling Strategy:**
*   **Client-Level Isolation:** Each provider has a dedicated client module (e.g., `app/services/byteme_client.py`). Within each client, API calls are wrapped in comprehensive `try-except` blocks. These blocks catch specific exceptions like `requests.exceptions.RequestException`, `HTTPError`, `Timeout`, JSON/XML/CSV parsing errors, and other potential issues.
*   **Graceful Degradation:** If an error occurs while fetching data from a specific provider, the client logs the error (to the server logs for debugging) and returns an empty list (`[]`) or `None`. This prevents a single failing API from crashing the entire offer aggregation process.
*   **Timeouts:** All external HTTP requests within the clients have explicit timeouts (e.g., 15-25 seconds) to prevent indefinite hanging.

### 2. Concurrent API Calls

To ensure a responsive user experience despite the need to call multiple external APIs, the main `/api/offers` route utilizes Python's `concurrent.futures.ThreadPoolExecutor`.
*   When a user submits an address, tasks for fetching data from each provider (and for WebWunder, each relevant connection type) are submitted to the thread pool.
*   These tasks execute concurrently, significantly reducing the overall wait time compared to sequential calls.
*   The main route uses `as_completed` to process results as they come in and has an overall timeout for each future's result, ensuring that even a misbehaving (very slow) provider client doesn't stall the entire response for too long.

### 3. Data Normalization

Each provider API returns data in a different format (XML, CSV, varied JSON structures). A crucial backend step is normalization:
*   Each provider client has a dedicated `_normalize_PROVIDER_offer()` function.
*   This function transforms the raw API response from that provider into a standardized JSON object structure. Common fields include:
    *   `providerName`
    *   `productName`
    *   `downloadSpeedMbps`, `uploadSpeedMbps`
    *   `monthlyPriceEur`, `monthlyPriceEurAfter2Years`
    *   `contractTermMonths`
    *   `connectionType`
    *   `benefits` (a summary string)
    *   `tv`, `discount`, `discountType`, `installationServiceIncluded`, `ageRestrictionMax`, `dataLimitGb`
    *   `_provider_specific_id` (for internal tracking/debugging)
*   This consistent structure simplifies data handling and display on the frontend.

### 4. Flask Application Structure

*   **App Factory Pattern (`create_app`):** The Flask application is initialized using an app factory in `app/__init__.py`. This allows for better organization and easier configuration.
*   **Blueprints:** API routes (e.g., `/api/offers`, `/api/share`) are organized using Flask Blueprints (`main_routes`).
*   **Environment Variables:** API keys, database credentials, and other sensitive configurations are managed via environment variables (loaded from a `.env` file for local development and set directly in the hosting environment for production).
*   **CORS:** `Flask-CORS` is used to handle Cross-Origin Resource Sharing, allowing the React frontend (if served on a different port during development) to communicate with the Flask API.

### 5. Share Link Feature (MySQL)

*   **Endpoint `/api/share` (POST):**
    *   Receives a list of currently displayed (and filtered/sorted) offers from the frontend.
    *   Generates a unique short ID (e.g., using `uuid`).
    *   Serializes the offer list to a JSON string.
    *   Stores the `shareId` and the `offers_json_string` in a MySQL database table (`shared_links`) using SQLAlchemy.
    *   The `SharedLink` SQLAlchemy model defines the table structure (`id`, `offers_json`, `created_at`).
*   **Endpoint `/api/share/<share_id>` (GET):**
    *   Retrieves the stored `offers_json_string` from the database using the provided `share_id`.
    *   Deserializes the JSON string back into a list of offer objects.
    *   Returns the offer data to the frontend.
*   **Database Robustness:** SQLAlchemy engine options (`pool_recycle`, `pool_pre_ping`) are configured to handle MySQL connection timeouts common in hosted environments like PythonAnywhere.

## Frontend Implementation (React & Chakra UI)

The frontend is a single-page application (SPA) built with React.

### 1. UI Components & Styling

*   **Chakra UI:** Used as the component library, providing a wide range of accessible and themeable UI components (Box, VStack, Button, Modal, Input, Select, etc.). This accelerates UI development and ensures a consistent, professional look and feel.
*   **Responsive Design:** Chakra UI's responsive style props (e.g., `w={{ base: "90%", md: "xl" }}`) are used to ensure the layout adapts to different screen sizes.
*   **Key Components:**
    *   `App.js`: Main component, handles routing, global state for offers, loading/error states, and orchestration of API calls via `handleAddressSubmit` and `handleShareResults`.
    *   `AddressForm.js`: A controlled component for user address input with client-side validation.
    *   `OfferList.js`: Renders a list of `OfferCard` components.
    *   `OfferCard.js`: Displays the details of a single internet offer in a structured and readable format. Includes logic to display provider logos.
    *   `SharedResultsPage.js`: Fetches and displays offers associated with a shared link ID.

### 2. Frontend Features

*   **Dynamic Offer Display:** Fetched offers are displayed with key details like speed, price, contract length, connection type, and other benefits.
*   **Sorting:** Users can sort the displayed offers by price (ascending/descending), speed (ascending/descending), and contract term.
*   **Filtering:** Users can filter offers based on:
    *   Connection Type
    *   Provider Name
    *   Contract Term (Months)
    *   Filter options are dynamically generated based on the values present in the current set of offers.
*   **Share Modal:**
    *   When users click "Share These Results," a modal appears.
    *   The frontend POSTs the currently `displayedOffers` (after filtering/sorting) to the `/api/share` backend endpoint.
    *   On success, the backend returns a `shareId`.
    *   The frontend constructs a full shareable URL (e.g., `yourdomain.com/share/<shareId>`).
    *   The modal displays this link with "Copy" and "Share on WhatsApp" buttons.
*   **Loading & Error States:**
    *   Spinners and loading text are shown during API calls.
    *   Clear error messages are displayed to the user if API calls fail or if form validation errors occur.

### 3. Client-Side State Persistence (`localStorage`)

To enhance user experience and meet the "session state" requirement:
*   **Last Searched Address:** The most recently submitted address details from `AddressForm.js` are saved to `localStorage` by `App.js` when a search is initiated. On subsequent visits or page reloads, `App.js` reads this stored address and passes it to `AddressForm` to pre-fill the input fields.
*   **Last Search Results:**
    *   When offers are successfully fetched by `App.js`, the `offers` array, the `hasSearched` status, and the current `sortBy` and filter selections are saved to `localStorage`.
    *   On page load, `App.js` attempts to load these stored results. If found, the `offers` list is populated, and the previous sorting/filtering state is reapplied, effectively restoring the user's last view.
    *   If a new search results in an error, the stored results are cleared to prevent showing stale data.

## Deployment

The application is deployed on [Railway.app](https://internet-provider-comparison.up.railway.app/). This is a video demonstration of the [Share link feature](https://youtu.be/VyQhrOGVDpI)
*   The Flask backend serves the static React build files.
*   Environment variables on PythonAnywhere are used for API keys and database credentials.
*   A MySQL database hosted on PythonAnywhere is used for the share link feature.

## Future Improvements / Optional Features Explored

*   **Address Autocompletion:** Could be added using a service like Google Places API.
*   **Input Validation:** Basic client-side validation is present; more comprehensive backend validation could be added.
*   **Advanced Caching:** For very high traffic, a more robust caching solution like Redis could be used for API responses instead `localStorage` for client-side views.

---
