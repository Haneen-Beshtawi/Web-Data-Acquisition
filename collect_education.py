"""Access plan: UCI documented API, dataset 697, one student record per row.
Collect two resources: API metadata JSON, then the CSV URL returned by the API.
Expected requests: 2. No credentials, guestbook or scraping. Preserve raw bytes.
Keep academic measures and outcomes, avoid demographic fields in cleaned data.
Custom names, raw/cleaned/output separation, validation and provenance support
Good Enough Practices. Run with Python 3.10+: py collect_education.py
"""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import sys
import time
from datetime import datetime, timezone
from urllib.request import urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent
API_URL = 'https://archive.ics.uci.edu/api/dataset?id=697'
FIELDS = {
    'Course': 'course_code',
    'Admission grade': 'admission_grade',
    'Curricular units 1st sem (enrolled)': 'semester1_units_enrolled',
    'Curricular units 1st sem (approved)': 'semester1_units_approved',
    'Curricular units 1st sem (grade)': 'semester1_grade',
    'Curricular units 2nd sem (approved)': 'semester2_units_approved',
    'Curricular units 2nd sem (grade)': 'semester2_grade',
    'Target': 'outcome',
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()

def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')

def download(url, log):
    for attempt in range(3):
        record = {'url': url, 'method': 'GET', 'started_utc': utc_now(), 'attempt': attempt + 1}
        log.append(record)
        try:
            with urlopen(url, timeout=60) as response:
                body = response.read()
                record.update(status=response.status, finished_utc=utc_now(), bytes=len(body))
                return body
        except HTTPError as error:
            record.update(status=error.code, finished_utc=utc_now())
            if error.code in (401, 403, 429) or error.code < 500 or attempt == 2:
                raise RuntimeError(f'HTTP {error.code}: request stopped; no access restriction bypassed.') from None
        except (URLError, TimeoutError, OSError):
            record.update(error='Network/timeout failure', finished_utc=utc_now())
            if attempt == 2:
                raise RuntimeError('Network request failed after three attempts.') from None
        time.sleep(2 ** attempt)
    raise RuntimeError('Download failed.')

def acquire():
    raw = ROOT / 'data/raw'
    raw.mkdir(parents=True, exist_ok=True)
    provenance_path = ROOT / 'outputs/provenance.json'
    if provenance_path.exists():
        provenance = json.loads(provenance_path.read_text())
        for filename, expected in provenance['raw_sha256'].items():
            path = raw / filename
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise RuntimeError('Raw snapshot missing or modified. Restore it before reproduction.')
        print('Reusing verified raw API snapshot; no new requests.')
        return provenance
    if any(raw.iterdir()):
        raise RuntimeError('Partial raw snapshot exists. Preserve it and use a fresh project folder for collection.')
    log = []
    started = utc_now()
    try:
        metadata_body = download(API_URL, log)
        payload = json.loads(metadata_body)
        if payload.get('status') != 200 or payload.get('data', {}).get('uci_id') != 697:
            raise RuntimeError('Unexpected API response or dataset identity.')
        metadata = payload['data']
        data_url = metadata.get('data_url', '')
        if not data_url.startswith('https://archive.ics.uci.edu/static/public/697/'):
            raise RuntimeError('Unexpected dataset URL returned by API; inspect metadata.')
        csv_body = download(data_url, log)
        reader = csv.DictReader(io.StringIO(csv_body.decode('utf-8-sig')))
        if not set(FIELDS).issubset(reader.fieldnames or []):
            raise RuntimeError('CSV schema changed; no raw data saved.')
        (raw / 'metadata.json').write_bytes(metadata_body)
        (raw / 'students_original.csv').write_bytes(csv_body)
    finally:
        save_json(ROOT / 'outputs/request_log.json', {'requests': log})
    provenance = {
        'source': metadata['name'], 'source_url': metadata['repository_url'],
        'doi': metadata['dataset_doi'], 'acquisition_method': 'Documented UCI API workflow',
        'api_documentation': 'https://github.com/uci-ml-repo/ucimlrepo',
        'api_endpoint': 'https://archive.ics.uci.edu/api/dataset',
        'query_parameters': {'id': 697}, 'data_url_returned_by_api': data_url,
        'collection_started_utc': started, 'collection_finished_utc': utc_now(),
        'http_attempts': len(log), 'expected_source_rows': metadata['num_instances'],
        'source_last_updated': metadata.get('last_updated'), 'api_version': 'No explicit version in endpoint',
        'account_required': False, 'api_key_required': False,
        'license': 'CC BY 4.0; credit dataset creators and describe modifications',
        'rate_limit': 'No numeric rate limit verified; only two sequential requests; cache reused',
        'raw_sha256': {'metadata.json': hashlib.sha256(metadata_body).hexdigest(),
                       'students_original.csv': hashlib.sha256(csv_body).hexdigest()},
        'python_version': sys.version,
        'reproduction_limit': 'Source and API can change; exact reproduction uses saved raw bytes and hashes.',
    }
    save_json(provenance_path, provenance)
    print('API collection successful; HTTP attempts:', len(log))
    return provenance

def clean():
    with (ROOT / 'data/raw/students_original.csv').open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if not set(FIELDS).issubset(reader.fieldnames or []):
            raise RuntimeError('Required fields missing.')
        rows = list(reader)
    fingerprints = [tuple(row.items()) for row in rows]
    duplicates = len(fingerprints) - len(set(fingerprints))
    if len(rows) < 100:
        raise RuntimeError('Fewer than 100 source observations.')
    cleaned = []
    for index, source in enumerate(rows, start=1):
        row = {'source_row': index}  # Snapshot row reference, NOT a real student ID.
        for source_name, target_name in FIELDS.items():
            text = source[source_name].strip()
            if target_name == 'outcome':
                if text not in {'Dropout', 'Enrolled', 'Graduate'}:
                    raise RuntimeError('Unknown outcome label; inspect source.')
                row[target_name] = text
            else:
                try:
                    number = float(text)
                except ValueError:
                    raise RuntimeError(f'Missing/non-numeric value in {source_name}; inspect source.') from None
                maximum = 200 if target_name == 'admission_grade' else 20 if target_name.endswith('_grade') else None
                if not math.isfinite(number) or number < 0 or (maximum is not None and number > maximum):
                    raise RuntimeError(f'Invalid value range for {source_name}.')
                if target_name in {'course_code', 'semester1_units_enrolled','semester1_units_approved','semester2_units_approved'}:
                    if not number.is_integer():
                        raise RuntimeError(f'Non-integer count/code in {source_name}.')
                    row[target_name] = int(number)
                else:
                    row[target_name] = number
        if row['semester1_units_approved'] > row['semester1_units_enrolled']:
            raise RuntimeError('Approved units exceed enrolled units; inspect source.')
        cleaned.append(row)
    output = ROOT / 'data/cleaned/students_cleaned.csv'
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=['source_row', *FIELDS.values()])
        writer.writeheader(); writer.writerows(cleaned)
    report = {'raw_rows': len(rows), 'cleaned_rows': len(cleaned), 'full_row_duplicates_flagged': duplicates,
              'duplicate_policy': 'No student ID is provided. Flag full-row matches; do not assume identical measures identify the same student.',
              'missing_selected_fields': 0, 'invalid_selected_values': 0,
              'steps': ['Select academic fields; exclude demographic and financial fields from cleaned data',
                        'Standardize descriptive column names and strip outer whitespace',
                        'Parse integer counts/codes and floating-point grades',
                        'Validate grade ranges, allowed labels and approved/enrolled relationship',
                        'Check complete source-row duplicates; retain distinct source observations'],
              'source_row_note': 'Local row reference for this immutable snapshot; not an identity or proof of unique individuals.',
              'schema': {'course_code':'categorical integer code; not a magnitude',
                         'admission_grade':'float, 0-200', 'semester_grades':'float, 0-20',
                         'unit_counts':'nonnegative integers','outcome':'Dropout / Enrolled / Graduate'}}
    save_json(ROOT / 'outputs/validation.json', report)
    print('Cleaned student observations:', len(cleaned))
    return cleaned

def analyze(rows):
    summaries = []
    for outcome in ('Dropout','Enrolled','Graduate'):
        group = [r for r in rows if r['outcome'] == outcome]
        summaries.append({'outcome': outcome, 'students': len(group),
                          'mean_semester1_grade': round(statistics.mean(r['semester1_grade'] for r in group),3),
                          'mean_semester1_units_approved': round(statistics.mean(r['semester1_units_approved'] for r in group),3)})
    with (ROOT / 'outputs/outcome_summary.csv').open('w',newline='',encoding='utf-8') as handle:
        writer = csv.DictWriter(handle,fieldnames=list(summaries[0]));writer.writeheader();writer.writerows(summaries)
    for row in summaries:print(row)
    # A tidy sample makes the cleaned structure visible without opening all records.
    sample_path = ROOT / 'outputs/cleaned_sample.csv'
    with sample_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows[:5])
    columns = ['source_row', 'course_code', 'admission_grade', 'semester1_units_approved', 'semester1_grade', 'outcome']
    lines = ['# Mini analysis: academic performance and recorded outcome', '',
             'Question: How do first-semester grade and approved units differ by recorded outcome?', '',
             '## Tidy sample', '',
             'The first five cleaned rows are shown below with selected columns. The accompanying cleaned_sample.csv contains all cleaned columns for these rows. source_row is a snapshot reference, not a student identity.', '',
             '| ' + ' | '.join(columns) + ' |',
             '| ' + ' | '.join(['---'] * len(columns)) + ' |']
    for row in rows[:5]:
        lines.append('| ' + ' | '.join(str(row[key]) for key in columns) + ' |')
    lines += ['', '## Descriptive comparison', '',
              '| Outcome | Students | Mean first-semester grade | Mean first-semester units approved |',
              '| --- | ---: | ---: | ---: |']
    for row in summaries:
        lines.append(f"| {row['outcome']} | {row['students']} | {row['mean_semester1_grade']} | {row['mean_semester1_units_approved']} |")
    lines += ['', '## Interpretation and cautions', '',
              'In this collected snapshot, the Graduate group has higher mean first-semester grades and approved units than the Dropout group. This is a descriptive association, not evidence that an intervention raising grades will cause graduation.', '',
              'These records come from one institutional setting. Outcome is measured at the end of the normal course duration; semester results are not available at admission. Using them as admission-time predictors would leak future information. Zero grades may have different explanations and should not be interpreted as lack of effort. '
              'The groups differ in size, and this comparison does not adjust for course or other differences.'
              ]
    (ROOT / 'outputs/MINI_ANALYSIS.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')

def main():
    global ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fresh', action='store_true', help='Collect again into a new dated folder; never overwrite old raw data.')
    args = parser.parse_args()
    if args.fresh:
        ROOT = ROOT / 'collections' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    print('Output folder:', ROOT)
    try:
        provenance = acquire()
        rows = clean()
        provenance['observations_collected'] = len(rows)
        save_json(ROOT / 'outputs/provenance.json', provenance)
        analyze(rows)
        return 0
    except (RuntimeError, OSError, ValueError, KeyError, csv.Error) as error:
        print('STOPPED:', error, file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
