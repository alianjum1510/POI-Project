import pandas as pd
import json
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from poi_importer_app.models import PoI
import gzip
from io import StringIO
from typing import Any
import re

class Command(BaseCommand):
    """
    Django management command to import Point of Interest (PoI) data from CSV, JSON, or XML files using pandas.
    This command can optionally delete all existing PoIs before importing new ones.
    """
    help = 'Import Point of Interest data from CSV, JSON, or XML files using pandas.'

    def add_arguments(self, parser):
        """
        Add custom arguments for this command.
        """
        parser.add_argument('file_paths', nargs='+', type=str)
        parser.add_argument('--reset', action='store_true', help='Delete all existing PoIs before importing')

    def handle(self, *args, **kwargs):
        """
        Loops through the provided file paths and imports data based on the file type.
        """
        file_paths = kwargs['file_paths']
        if kwargs.get('reset'):
            PoI.objects.all().delete()
            self.stdout.write(self.style.WARNING('All existing PoIs deleted (reset).'))
        for file_path in file_paths:
            file_extension = file_path.split('.')[-1].lower()
            self.stdout.write(f"Processing file: {file_path}")

            if file_extension == 'csv':
                self.import_csv(file_path)
            elif file_extension == 'json':
                self.import_json(file_path)
            elif file_extension == 'xml':
                self.import_xml(file_path)
            else:
                self.stdout.write(self.style.ERROR(f'Unsupported file format for {file_path}!'))

    def import_csv(self, file_path):
        """
        Imports data from a CSV file and processes it.
        
        Args:
            file_path (str): Path to the CSV file.
        """
        try:
            df = pd.read_csv(file_path)
            self.stdout.write(f"Processing CSV with {len(df)} rows and columns: {list(df.columns)}")
            
            # renaming column to standardized fields in the modal
            column_mapping = {
                'poi_id': 'poi_id',
                'poi_name': 'name', 
                'poi_category': 'category',
                'poi_latitude': 'latitude',
                'poi_longitude': 'longitude',
                'poi_ratings': 'ratings'
            }
            
            for old_name, new_name in column_mapping.items():
                if old_name in df.columns:
                    df = df.rename(columns={old_name: new_name})
            
            self.process_dataframe(df, 'CSV')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV file: {e}"))

    def import_json(self, file_path):
        """
        Imports data from a JSON file and processes it.
        
        Args:
            file_path (str): Path to the JSON file.
        """
        try:

            df = pd.read_json(file_path)
            self.stdout.write(f"Processing JSON with {len(df)} rows and columns: {list(df.columns)}")
            
            # extracting longitude and latitude seprately
            if 'coordinates' in df.columns:
                df['latitude'] = df['coordinates'].apply(lambda x: x.get('latitude') if isinstance(x, dict) else None)
                df['longitude'] = df['coordinates'].apply(lambda x: x.get('longitude') if isinstance(x, dict) else None)
                df = df.drop('coordinates', axis=1)
            

            # column name mapping
            if 'id' in df.columns:
                df = df.rename(columns={'id': 'poi_id'})
            
            self.process_dataframe(df, 'JSON')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading JSON file: {e}"))

    def import_xml(self, file_path):
        """
        Imports data from an XML file (supporting gzip compression) and processes it.
        
        Args:
            file_path (str): Path to the XML file.
        """
        try:
            try:
                with open(file_path, 'rb') as f:
                    raw = f.read()
            except FileNotFoundError:
                self.stdout.write(self.style.ERROR(f"XML file not found: {file_path}"))
                return
             
            # check if file is gzip-compressed if yes then de-compress it
            if len(raw) >= 2 and raw[0] == 0x1F and raw[1] == 0x8B:
                try:
                    raw = gzip.decompress(raw)
                except OSError:
                    pass

            # decoding raw bites into string
            text = raw.decode('utf-8-sig', errors='replace')
            first_lt = text.find('<')
            if first_lt > 0:
                text = text[first_lt:]
            text = text.lstrip()

            #sanitizing the data
            def _sanitize_ampersands(s: str) -> str:
                pattern = re.compile(r"&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9A-Fa-f]+;)")
                return pattern.sub("&amp;", s)
            text = _sanitize_ampersands(text)


            # load the data in data-frame
            df = pd.read_xml(StringIO(text), xpath='.//DATA_RECORD')
            self.stdout.write(f"Processing XML with {len(df)} rows and columns: {list(df.columns)}")
            
            # renaming column to standardized fields in the modal
            column_mapping = {
                'pid': 'poi_id',
                'pname': 'name',
                'pcategory': 'category', 
                'platitude': 'latitude',
                'plongitude': 'longitude',
                'pratings': 'ratings'
            }
            
            df = df.rename(columns=column_mapping)
            
            self.process_dataframe(df, 'XML')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading XML file: {e}"))

    def process_dataframe(self, df, file_type):
        """Process the pandas DataFrame and import POIs"""
        # identifies total numer of records poccessed,error occured and if record exist than the duplicate
        success_count = 0
        error_count = 0
        duplicate_count = 0
        
        for index, row in df.iterrows():
            try:

                poi_id_val = row.get('poi_id')
                name_val = row.get('name')
                category_val = row.get('category')
                
                # skipping if any of the value is missing for now
                if poi_id_val is None or (hasattr(poi_id_val, '__len__') and len(poi_id_val) == 0):
                    continue
                if name_val is None or (hasattr(name_val, '__len__') and len(name_val) == 0):
                    continue
                if category_val is None or (hasattr(category_val, '__len__') and len(category_val) == 0):
                    continue
                
                poi_id = int(poi_id_val)
                name = str(name_val).strip()
                category = str(category_val).strip()
                
                try:
                    latitude_val = row['latitude']
                    longitude_val = row['longitude']
                    
                    # if there is issue with co-ordinates then skip the records also for now
                    if pd.isna(latitude_val) or pd.isna(longitude_val):
                        self.stdout.write(self.style.WARNING(f"Row {index + 1}: Missing coordinates, skipping"))
                        continue
                        
                    latitude = float(latitude_val)
                    longitude = float(longitude_val)
                except (ValueError, TypeError):
                    self.stdout.write(self.style.WARNING(f"Row {index + 1}: Invalid coordinates, skipping"))
                    continue
                
                # parsing the rating as it is iterable
                ratings = self.parse_ratings(row.get('ratings', []))
                
                # create the record but if poi_id is present update that record
                obj, created = PoI.objects.update_or_create(
                    poi_id=poi_id,
                    defaults={
                        'name': name,
                        'category': category,
                        'latitude': latitude,
                        'longitude': longitude,
                        'ratings': ratings,
                    }
                )
                
                success_count += 1
                if success_count % 100 == 0:  
                    self.stdout.write(f"Processed {success_count} records...")
                
            except IntegrityError:
                duplicate_count += 1
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f"Row {index + 1}: Error - {e}"))
        
        self.stdout.write(self.style.SUCCESS(
            f"{file_type} Import Complete: {success_count} imported/updated, {duplicate_count} duplicates, {error_count} errors"
        ))

    def parse_ratings(self, ratings_data):
        """Parse ratings from various formats into a list of floats"""

        if ratings_data is None:
            return []

        try:
            from pandas import Series
            array_types = (list, tuple, set, Series)
        except ImportError:
            array_types = (list, tuple, set)

        if isinstance(ratings_data, array_types):
            result = []
            for item in list(ratings_data):
                if item is None:
                    continue
                try:
                    if isinstance(item, float) and pd.isna(item):
                        continue
                except Exception:
                    pass
                try:
                    result.append(float(item))
                except (ValueError, TypeError):
                    continue
            return result

        if isinstance(ratings_data, str):
            ratings_str = ratings_data.strip()
            if ratings_str.startswith('{') and ratings_str.endswith('}'):
                ratings_str = ratings_str[1:-1]
            if not ratings_str:
                return []
            try:
                return [float(r.strip()) for r in ratings_str.split(',') if r.strip()]
            except ValueError:
                return []

        try:
            return [float(ratings_data)]
        except (ValueError, TypeError):
            return []
