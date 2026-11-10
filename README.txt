================================================================================
ATMosphere — ATM Social Map System Overview
================================================================================

1. APPLICATION OVERVIEW
ATMosphere is a crowd-sourced ATM locator web application designed for the
Philippine context (configured with Asia/Manila timezone). It addresses the
unreliability of ATM cash availability, operational uptime, and transaction fee
clarity by enabling users to locate nearby ATMs and share real-time operational
status. Target users are banking customers and commuters seeking operational ATMs.

2. CORE FEATURES
- Interactive Map & Nearby Discovery: Visualizes ATM locations using Leaflet.js
  with GeoJSON feeds, calculating distances via Haversine or spatial queries.
- Operational Status Reporting: Authenticated users submit real-time reports
  indicating whether an ATM is online and has cash.
- Issue & Discrepancy Reporting: Users report fee discrepancies, inaccurate
  pin coordinates, or general notes.
- ATM Contribution: Authenticated users can submit new ATM pins with associated
  bank, coordinates, address, and supported card networks.
- User Management: Account registration, session login/logout, password change,
  and profile display name management.

3. TECHNOLOGY STACK
- Language: Python 3.14
- Frameworks: Django 6.1.1, Django REST Framework (DRF) 3.18.1, GeoDjango
- Extensions/Libraries: rest_framework_gis 1.3.0, python-dotenv 1.2.3,
  psycopg2-binary 2.9.13 (for PostGIS), psycopg 3.3.5, Leaflet.js (CDN)
- Database: Supabase PostgreSQL with PostGIS extension enabled
- Native Dependencies (Windows): OSGeo4W (GDAL, GEOS, PROJ DLLs)

4. PROJECT STRUCTURE
- config/: Project settings (settings.py), root routing (urls.py), and WSGI.
- apps/atms/: Core ATM domain containing models (ATM, Bank, CardNetwork,
  NetworkAlliance, ATMNetwork, StatusReport, ATMReport), DRF serializers,
  API views, and routes (/api/atms/).
- apps/home/: Map dashboard view and home.html template containing the Leaflet UI.
- apps/login/, apps/register/: Authentication controllers, forms, and templates.
- apps/profile/, apps/settings/: UserProfile management and password updates.
- static/: Assets (CSS, images, JS stubs).
- templates/: Django HTML templates for all views.

5. IMPLEMENTATION DETAILS
- Architecture: Hybrid architecture pairing server-rendered Django templates with
  a REST/GeoJSON API consumed via vanilla JS Leaflet.js.
- GIS Integration: Fallback design in apps/atms/models.py checks HAS_GIS; uses
  PointField and spatial queries if PostGIS/GDAL are active, falling back to
  DecimalField latitude/longitude and Haversine formula calculation.
- Authentication & AuthZ: Django session authentication. DRF endpoints use
  IsAuthenticatedOrReadOnly (reads are public, writes require login).
- User Profiles: apps/profile/models.py attaches UserProfile to Django's auth User
  via post_save signals.

6. FEATURE DEVELOPMENT GUIDANCE
- Adding ATM attributes: Update apps/atms/models.py, serializers.py
  (ATMGeoSerializer/ATMCreateSerializer), and home.html.
- New API Endpoints: Add views to apps/atms/views.py and route in apps/atms/urls.py.
- Migrations & GIS: Modifying spatial fields requires PostGIS and proper GDAL
  native library configuration in settings.py (configured for C:\OSGeo4W).

7. RUNNING AND TESTING
- Setup:
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    cp .env.example .env  # Configure Supabase DB credentials
- Run Server:
    python manage.py migrate
    python manage.py runserver
- Testing:
    python manage.py test apps.home apps.login apps.profile apps.register apps.settings
  (Note: apps.atms test suite is not implemented in existing codebase).
