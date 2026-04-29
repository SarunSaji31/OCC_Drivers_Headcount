import csv
import logging
import os
from datetime import datetime, timedelta

import chardet
import pandas as pd

from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.shortcuts import render

from ..models import EKSTMDailyTrips, EKSTMMileage, EKSTMSalik, Unit

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.join(settings.MEDIA_ROOT, 'uploads')
DOWNLOAD_DIR = os.path.join(settings.MEDIA_ROOT, 'downloads')
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

_SPECIFIC_GROUPINGS = {
    "EM6 TALAL QAMZI": ["EM6", "Talal", "Al Qamzi"],
    "SARAB SAFA": ["SARAB", "SAFA"],
    "SABREEN FALTAT MANAZIL TOWER": ["SAB", "FT", "MT"],
    "SONBOULAH GARHOUD TOWERS": ["SON", "GT"],
    "TECOM DR.KHALIFA": ["TECOM", "Dr. K"],
    "MILLENIUM PINK GROSVENOR": ["MIT", "PINK", "GCT"],
    "PARK ZABEEL 7 PEARLS": ["PZABEEL", "7Pearls"],
    "DSO": ["DSO"],
}

_NAME_MAPPING = {
    "Talal": "TALAL", "Al Qamzi": "QAMZI", "EM6": "EM6",
    "Dr. K": "DR.KHALIFA", "TECOM": "TECOM 1,2", "GCT": "GROSVENOUR",
    "PINK": "PINK", "SAB": "SABREEN", "FT": "FALTAT",
    "MT": "MANAZIL TOWER", "SON": "SONBOULAH", "GT": "GARHOUD TOWERS",
    "MIT": "MILLINUM TOWER", "PZABEEL": "PARK ZABEEL 1,2",
    "7Pearls": "7 PEARLS", "DSO": "DSO",
}


def _calculate_units(crew_count):
    return (crew_count - 1) // 31 + 1 if crew_count > 0 else 0


def _process_data(df, direction):
    grouped_data = []
    for _, row in df.iterrows():
        time = row["TIME"]
        if isinstance(time, str):
            time = datetime.strptime(time, '%H:%M').time()
        if direction == "Outbound":
            time = (datetime.combine(datetime.today(), time) + timedelta(minutes=14)).time()
        formatted_time = time.strftime('%H:%M')

        for group_name, buildings in _SPECIFIC_GROUPINGS.items():
            crew_count = 0
            valid_buildings = []
            for building in buildings:
                if building in df.columns:
                    val = row[building]
                    if pd.notna(val) and val > 0:
                        crew_count += val
                        valid_buildings.append(_NAME_MAPPING.get(building, building))
            if crew_count > 0:
                grouped_data.append({
                    "DATE": (datetime.now() + timedelta(days=1)).strftime("%d-%b"),
                    "NO OF UNITS": _calculate_units(crew_count),
                    "TIME": formatted_time,
                    "FROM": ", ".join(valid_buildings) if direction == "Inbound" else "EAC-C",
                    "TO": "EAC-C" if direction == "Inbound" else ", ".join(valid_buildings),
                    "CREW": crew_count,
                })
    return pd.DataFrame(grouped_data)


def _process_files(inbound_file, outbound_file):
    df_in = pd.read_excel(inbound_file)
    df_out = pd.read_excel(outbound_file)
    df_in.columns = df_in.columns.str.strip()
    df_out.columns = df_out.columns.str.strip()

    cols = ['DATE', 'NO OF UNITS', 'TIME', 'FROM', 'TO', 'CREW']
    df_in_grouped = _process_data(df_in, "Inbound")[cols]
    df_out_grouped = _process_data(df_out, "Outbound")[cols]

    inbound_path = os.path.join(DOWNLOAD_DIR, 'Cabin_crew_inbound_trips.xlsx')
    outbound_path = os.path.join(DOWNLOAD_DIR, 'Cabin_crew_outbound_trips.xlsx')
    df_in_grouped.to_excel(inbound_path, index=False)
    df_out_grouped.to_excel(outbound_path, index=False)
    return inbound_path, outbound_path


def upload_view(request):
    if request.method == 'POST' and request.FILES.get('inbound_file') and request.FILES.get('outbound_file'):
        try:
            inbound_path, outbound_path = _process_files(request.FILES['inbound_file'], request.FILES['outbound_file'])
            return render(request, 'duty/upload.html', {
                'inbound_path': f'/download/{os.path.basename(inbound_path)}',
                'outbound_path': f'/download/{os.path.basename(outbound_path)}',
            })
        except Exception as e:
            return render(request, 'duty/upload.html', {'error': str(e)})
    return render(request, 'duty/upload.html')


def download_file(request, filename):
    file_path = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)
    return HttpResponse("File not found.", status=404)


def upload_gpsreports(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        decoded_file = request.FILES['csv_file'].read().decode('utf-8-sig').splitlines()
        if not decoded_file:
            return HttpResponse("CSV file is empty.", status=400)

        required_keys = ['unit', 'routetime', 'ride_date', 'route_id', 'first_point', 'route_group', 'route_type']
        for idx, row in enumerate(csv.DictReader(decoded_file), start=1):
            row_lower = {k.strip().lower(): v.strip() for k, v in row.items() if k}
            missing = [k for k in required_keys if k not in row_lower or not row_lower[k]]
            if missing:
                return HttpResponse(
                    f"Row {idx} missing fields: {', '.join(missing)}. Available: {', '.join(row_lower.keys())}",
                    status=400,
                )
            try:
                ride_date = datetime.strptime(row_lower['ride_date'], '%d/%m/%Y').date()
            except ValueError:
                return HttpResponse(f"Row {idx}: Invalid date format. Use dd/mm/YYYY.", status=400)

            unit_obj, _ = Unit.objects.get_or_create(code=row_lower['unit'])
            EKSTMDailyTrips.objects.update_or_create(
                unit=unit_obj,
                routetime=row_lower['routetime'],
                ride_date=ride_date,
                route_id=row_lower['route_id'],
                defaults={
                    'shift_out': row_lower.get('shift_out', ''),
                    'shift_in': row_lower.get('shift_in', ''),
                    'first_point': row_lower['first_point'],
                    'route_group': row_lower['route_group'],
                    'route_type': row_lower['route_type'],
                    'driver_name': row_lower.get('driver_name', ''),
                },
            )
        return HttpResponse("GPS report file uploaded successfully!")
    return render(request, 'duty/stm_gpsreports_upload.html')


def upload_salik(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        decoded_file = request.FILES['csv_file'].read().decode('cp1252').splitlines()
        if not decoded_file:
            return HttpResponse("CSV file is empty.", status=400)

        required_keys = ['unit', 'salik_start_date', 'salik_satrt_time', 'initial_location', 'final_location', 'crossing_rate']
        for idx, row in enumerate(csv.DictReader(decoded_file), start=1):
            row_lower = {k.strip().lower(): v.strip() for k, v in row.items() if k}
            missing = [k for k in required_keys if k not in row_lower or not row_lower[k]]
            if missing:
                return HttpResponse(
                    f"Row {idx} missing fields: {', '.join(missing)}. Available: {', '.join(row_lower.keys())}",
                    status=400,
                )
            try:
                salik_start_date = datetime.strptime(row_lower['salik_start_date'], '%d/%m/%Y').date()
            except ValueError:
                return HttpResponse(f"Row {idx}: Invalid date format. Use dd/mm/YYYY.", status=400)

            unit_obj, _ = Unit.objects.get_or_create(code=row_lower['unit'])
            EKSTMSalik.objects.update_or_create(
                unit=unit_obj,
                salik_start_date=salik_start_date,
                salik_satrt_time=row_lower['salik_satrt_time'],
                routeid=row_lower.get('routeid', ''),
                defaults={
                    'initial_location': row_lower['initial_location'],
                    'final_location': row_lower['final_location'],
                    'driver_name': row_lower.get('driver_name', ''),
                    'crossing_rate': row_lower['crossing_rate'],
                    'routetype': row_lower.get('routetype', ''),
                    'shift_in': row_lower.get('shift_in', ''),
                    'shift_out': row_lower.get('shift_out', ''),
                    'routegroup': row_lower.get('routegroup', ''),
                },
            )
        return HttpResponse("Salik file uploaded successfully!")
    return render(request, 'duty/stm_gpsreports_upload.html')


def upload_mileage(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        raw_data = request.FILES['csv_file'].read()
        detected = chardet.detect(raw_data)
        encoding = detected['encoding'] or 'utf-8'
        try:
            decoded_file = raw_data.decode(encoding).splitlines()
        except UnicodeDecodeError:
            decoded_file = raw_data.decode('latin1', errors='replace').splitlines()

        reader = csv.reader(decoded_file)
        next(reader, None)
        data_uploaded = False

        for idx, row in enumerate(reader, start=1):
            if not row or len(row) < 3:
                continue
            date_str, unit_code, mileage = row[0].strip(), row[1].strip(), row[2].strip()
            try:
                mileage_date = datetime.strptime(date_str, '%d/%m/%Y').date()
            except ValueError:
                return HttpResponse(f"Row {idx} has invalid date format: {date_str}", status=400)
            unit, _ = Unit.objects.get_or_create(code=unit_code)
            EKSTMMileage.objects.update_or_create(unit=unit, date=mileage_date, defaults={'mileage': mileage})
            data_uploaded = True

        if data_uploaded:
            return HttpResponse("Mileage file uploaded successfully!")
        return HttpResponse("No valid data found to upload.", status=400)

    return render(request, 'duty/stm_gpsreports_upload.html')
