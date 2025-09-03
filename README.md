PoI Importer – Take-Home Project
This Django application imports Point of Interest (PoI) data from various structured file formats (CSV, JSON, XML) into a local database and allows users to browse, search, and filter the data via the Django Admin interface.

# Features
Built with Python 3.10+ and Django

Supports importing PoI data from:
.csv, .json, and .xml files

Includes a custom import_pois management command:
python manage.py import_pois <file1> <file2> ...

Provides a searchable and filterable Admin UI for:
Internal ID
External ID
Category
Average Rating


# Admin Features
Search: by internal ID or external ID
Filter: by category
View: name, category, and average rating for each PoI
This project demonstrates file parsing, data modeling, admin customization, and CLI tooling—all essential for production-ready Django apps.


# PROJECT SETUP
# 1 Get the code
git clone <repository_url>
cd <project_directory>

# 2 Create & activate virtualenv
python3 -m venv venv
# macOS/Linux:
source venv/bin/activate
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# 3 Install dependencies
pip install -r requirements.txt

# 4 Apply migrations
python manage.py migrate

# 5 Create an admin user
python manage.py createsuperuser

# 6 Run the server
python manage.py runserver

Admin URL: http://127.0.0.1:8000/admin/

# 7 Importing Data 
# Single file
python manage.py import_pois /path/to/pois.csv
# multiple file (space‑separated)
python manage.py import_pois /path/to/pois.csv /path/to/pois.json