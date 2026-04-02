"""
OCR-based document verification service.
Priority: Google Cloud Vision -> Tesseract -> Manual fallback
"""
import os
import re
import uuid
from PIL import Image

# -- Tesseract (optional) -----------------------------------------------------
try:
    import pytesseract
    for _p in [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Tesseract-OCR', 'tesseract.exe'),
    ]:
        if os.path.exists(_p):
            pytesseract.pytesseract.tesseract_cmd = _p
            break
    pytesseract.get_tesseract_version()
    TESSERACT_OK = True
except Exception:
    TESSERACT_OK = False

# -- PyMuPDF ------------------------------------------------------------------
try:
    import fitz
    PYMUPDF_OK = True
except ImportError:
    PYMUPDF_OK = False

# -- OpenCV -------------------------------------------------------------------
try:
    import cv2
    import numpy as np
    CV2_OK = True
except ImportError:
    CV2_OK = False

UPLOAD_DIR = os.path.join('static', 'uploads', 'kyc_documents')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
MAX_BYTES = 5 * 1024 * 1024


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_document(file_storage):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = file_storage.filename.rsplit('.', 1)[1].lower()
    path = os.path.join(UPLOAD_DIR, '{}.{}'.format(uuid.uuid4().hex, ext))
    file_storage.save(path)
    return path


# -- Image quality check ------------------------------------------------------

def check_image_quality(file_path):
    ext = file_path.rsplit('.', 1)[-1].lower()
    if ext == 'pdf':
        return {'ok': True, 'reason': ''}
    if not CV2_OK:
        return {'ok': True, 'reason': ''}

    img = cv2.imread(file_path)
    if img is None:
        return {'ok': False, 'reason': 'Could not read image. Please upload a valid PNG or JPG.'}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    blur = cv2.Laplacian(gray, cv2.CV_64F).var()
    print('[QC] blur={:.1f}'.format(blur))
    if blur < 30:
        return {'ok': False, 'reason': 'Image is too blurry. Please upload a clear, well-lit document photo.'}

    brightness = gray.mean()
    print('[QC] brightness={:.1f}'.format(brightness))
    if brightness < 40:
        return {'ok': False, 'reason': 'Image is too dark. Please upload a well-lit document photo.'}
    if brightness > 230:
        return {'ok': False, 'reason': 'Image is overexposed. Please reduce glare and re-upload.'}

    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    if os.path.exists(cascade_path):
        faces = cv2.CascadeClassifier(cascade_path).detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
        for (fx, fy, fw, fh) in faces:
            ratio = (fw * fh) / (h * w)
            print('[QC] face ratio={:.2f}'.format(ratio))
            if ratio > 0.25:
                return {'ok': False, 'reason': 'This looks like a selfie. Please upload a government ID document.'}

    if w < 200 or h < 150:
        return {'ok': False, 'reason': 'Image resolution too low. Please upload a higher quality photo.'}

    return {'ok': True, 'reason': ''}


# -- Text extraction ----------------------------------------------------------

def extract_text(file_path):
    ext = file_path.rsplit('.', 1)[-1].lower()
    return _pdf_text(file_path) if ext == 'pdf' else _image_text(file_path)


def _pdf_text(file_path):
    if not PYMUPDF_OK:
        return ''
    try:
        doc = fitz.open(file_path)
        text = '\n'.join(page.get_text() for page in doc)
        if len(text.strip()) < 30 and TESSERACT_OK:
            print('[OCR] Scanned PDF - rendering for OCR')
            parts = []
            for page in doc:
                pix = page.get_pixmap(dpi=200)
                img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
                parts.append(pytesseract.image_to_string(img, lang='eng', config='--oem 3 --psm 6'))
            text = '\n'.join(parts)
        doc.close()
        print('[OCR] PDF chars={}'.format(len(text)))
        print('[OCR] Preview:\n{}'.format(text[:400]))
        return text
    except Exception as e:
        print('[OCR] PDF error: {}'.format(e))
        return ''


def _preprocess_image(img_cv):
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    if w < 1000:
        scale = 1000.0 / w
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10)
    return thresh


def _image_text(file_path):
    """Surepass OCR -> Google Vision -> Tesseract -> __NO_OCR__"""
    from dotenv import load_dotenv
    load_dotenv(override=True)

    # Option 1: Surepass OCR upload (primary — uses existing token)
    # Returns extracted text directly; caller passes doc_type separately
    # We store the raw Surepass response in a module-level cache for extract_name to use
    surepass_result = _surepass_ocr(file_path)
    if surepass_result:
        print('[OCR] Surepass OCR success')
        return surepass_result

    # Option 2: Google Cloud Vision
    creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '').strip()
    if creds and os.path.exists(creds):
        gv = _google_vision_text(file_path)
        if gv and len(gv.strip()) > 10:
            print('[OCR] Google Vision chars={}'.format(len(gv)))
            return gv
        print('[OCR] Google Vision empty')
    else:
        print('[OCR] Google Vision not configured')

    # Option 3: Tesseract
    if TESSERACT_OK:
        try:
            img_cv = cv2.imread(file_path) if CV2_OK else None
            if img_cv is not None:
                processed = _preprocess_image(img_cv)
                img_pil = Image.fromarray(processed)
                text = pytesseract.image_to_string(img_pil, lang='eng', config='--oem 3 --psm 6')
                if len(text.strip()) < 20:
                    text = pytesseract.image_to_string(img_pil, lang='eng', config='--oem 3 --psm 3')
            else:
                img_pil = Image.open(file_path)
                text = pytesseract.image_to_string(img_pil, lang='eng', config='--oem 3 --psm 6')
            print('[OCR] Tesseract chars={}'.format(len(text)))
            return text
        except Exception as e:
            print('[OCR] Tesseract error: {}'.format(e))

    print('[OCR] No OCR engine available')
    return '__NO_OCR__'


# Module-level cache: stores last Surepass OCR name so extract_name can return it directly
_surepass_name_cache = {'name': ''}


def _surepass_ocr(file_path):
    """
    Call Surepass OCR upload endpoint.
    Returns a synthetic text string with 'Name: <name>' so the existing
    extract_name pipeline can parse it, or empty string on failure.
    """
    import requests as req
    token = os.getenv('SUREPASS_TOKEN', '').strip()
    if not token or token == 'your_surepass_bearer_token':
        print('[OCR] Surepass token not configured')
        return ''

    # We don't know doc_type here, so try a generic OCR endpoint.
    # Surepass has per-doc OCR upload endpoints; we'll try them in order
    # based on what's stored in the cache from the route call.
    doc_type = _surepass_name_cache.get('doc_type', '')
    endpoint = _surepass_ocr_endpoint(doc_type)
    if not endpoint:
        print('[OCR] No Surepass OCR endpoint for doc_type={}'.format(doc_type))
        return ''

    try:
        with open(file_path, 'rb') as f:
            ext = file_path.rsplit('.', 1)[-1].lower()
            mime = 'application/pdf' if ext == 'pdf' else 'image/jpeg'
            files = {'file': (os.path.basename(file_path), f, mime)}
            headers = {'Authorization': 'Bearer {}'.format(token)}
            resp = req.post(endpoint, headers=headers, files=files, timeout=15)

        print('[OCR] Surepass status={} body={}'.format(resp.status_code, resp.text[:300]))

        if resp.status_code != 200:
            return ''

        data = resp.json()
        if not data.get('success'):
            print('[OCR] Surepass OCR failed: {}'.format(data.get('message', '')))
            return ''

        d = data.get('data') or {}
        # Extract name from response — field names vary by doc type
        name = (
            d.get('name') or d.get('full_name') or d.get('pan_holder_name') or
            d.get('holder_name') or d.get('name_on_card') or
            ('{} {}'.format(d.get('first_name', ''), d.get('last_name', ''))).strip() or ''
        ).strip()

        print('[OCR] Surepass extracted name: {!r}'.format(name))
        _surepass_name_cache['name'] = name

        if name:
            # Return synthetic text that our name extractor can parse
            return 'Name: {}\n'.format(name)
        return ''

    except Exception as e:
        print('[OCR] Surepass OCR exception: {}'.format(e))
        return ''


def _surepass_ocr_endpoint(doc_type):
    """Map document type to Surepass OCR upload endpoint."""
    dt = (doc_type or '').lower()
    if 'pan' in dt:
        return 'https://kyc-api.surepass.io/api/v1/pan/upload'
    elif 'aadhaar' in dt or 'aadhar' in dt:
        return 'https://kyc-api.surepass.io/api/v1/aadhaar/upload'
    elif 'voter' in dt:
        return 'https://kyc-api.surepass.io/api/v1/voter-id/upload'
    elif 'driving' in dt or 'licen' in dt:
        return 'https://kyc-api.surepass.io/api/v1/driving-license/upload'
    elif 'passport' in dt:
        return 'https://kyc-api.surepass.io/api/v1/passport/upload'
    return ''


def _google_vision_text(file_path):
    try:
        from google.cloud import vision as gv
        client = gv.ImageAnnotatorClient()
        with open(file_path, 'rb') as f:
            content = f.read()
        image = gv.Image(content=content)
        response = client.text_detection(image=image)
        if response.error.message:
            print('[OCR] Google Vision error: {}'.format(response.error.message))
            return ''
        texts = response.text_annotations
        return texts[0].description if texts else ''
    except Exception as e:
        print('[OCR] Google Vision exception: {}'.format(e))
        return ''


# -- Document-specific name extraction ----------------------------------------

_NAME_RE = re.compile(r'^[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){1,4}$')
_JUNK = re.compile(
    r'\b(government|india|republic|income|tax|department|authority|'
    r'election|commission|driving|licence|license|passport|voter|'
    r'aadhaar|uid|valid|expiry|issue|father|mother|husband|wife|'
    r'address|dob|date|birth|permanent|account|number|card|'
    r'signature|photo|male|female|other|print)\b',
    re.IGNORECASE
)


def _lines(text):
    return [l.strip() for l in text.splitlines() if l.strip()]


def _is_name(s):
    return bool(_NAME_RE.match(s)) and not _JUNK.search(s)


def _after_label(lines, label_re):
    skip_re = re.compile(r"\b(father|mother|husband|wife|guardian|care.of|s/o|d/o|w/o)\b", re.IGNORECASE)
    for i, line in enumerate(lines):
        if skip_re.search(line):
            continue
        if label_re.search(line):
            parts = re.split(r'[:\-]', line, maxsplit=1)
            if len(parts) == 2:
                c = re.sub(r'[^A-Za-z\s].*$', '', parts[1]).strip().title()
                if _is_name(c):
                    return c
            for j in range(i + 1, min(i + 4, len(lines))):
                if skip_re.search(lines[j]):
                    break
                c = re.sub(r'[^A-Za-z\s].*$', '', lines[j]).strip().title()
                if _is_name(c):
                    return c
    return ''


def _pan_name(lines):
    for i, line in enumerate(lines):
        if re.search(r'\b(date.of.birth|dob)\b', line, re.IGNORECASE):
            for j in range(i - 1, max(i - 5, -1), -1):
                c = lines[j].strip()
                if re.match(r'^[A-Z][A-Z ]{3,}$', c) and not _JUNK.search(c):
                    return c.title()
    for line in lines:
        if re.match(r'^[A-Z][A-Z ]{3,40}$', line) and not _JUNK.search(line):
            if 2 <= len(line.split()) <= 5:
                return line.title()
    return ''


def _aadhaar_name(lines):
    for i, line in enumerate(lines):
        if re.search(r'\b(dob|date.of.birth|yob)\b', line, re.IGNORECASE):
            for j in range(i - 1, max(i - 4, -1), -1):
                c = lines[j].strip().title()
                if _is_name(c):
                    return c
    return _after_label(lines, re.compile(r'\bname\b', re.IGNORECASE))


def _voter_name(lines):
    skip_re = re.compile(r"\b(father|mother|husband|wife|guardian|care.of|s/o|d/o|w/o)\b", re.IGNORECASE)

    for line in lines:
        if skip_re.search(line):
            continue
        # Look for "Name:" anywhere in the line (Voter ID has prefix noise)
        m = re.search(r'\bName\s*:\s*([A-Za-z][A-Za-z\s]{3,50})', line)
        if m:
            c = re.sub(r'[^A-Za-z\s].*$', '', m.group(1)).strip().title()
            if _is_name(c):
                return c

    # Fallback: any proper-name line
    for line in lines:
        if skip_re.search(line):
            continue
        c = re.sub(r'[^A-Za-z\s].*$', '', line).strip().title()
        if _is_name(c):
            return c
    return ''


def _dl_name(lines):
    skip_re = re.compile(r"\b(father|mother|husband|wife|guardian|s/o|d/o|w/o|sow|dob|address|pin|road|dist|tq)\b", re.IGNORECASE)

    # Pattern 1: "Name:" or OCR-typo variants like "Kame:", "Nane:", "Mame:"
    name_label = re.compile(r'\b[KNMkn][aA][mM][eE]\s*:', re.IGNORECASE)
    for line in lines:
        if skip_re.search(line):
            continue
        m = name_label.search(line)
        if m:
            rest = line[m.end():].strip()
            c = re.sub(r'[^A-Za-z\s].*$', '', rest).strip().title()
            if _is_name(c):
                return c

    # Pattern 2: ALL-CAPS name after "Name:" anywhere
    for line in lines:
        if skip_re.search(line):
            continue
        m = re.search(r'[Nn]ame\s*[:\-]\s*([A-Z][A-Z\s]{3,40})', line)
        if m:
            c = m.group(1).strip().title()
            c = re.sub(r'[^A-Za-z\s].*$', '', c).strip()
            if _is_name(c):
                return c

    # Pattern 3: standalone ALL-CAPS line (DL often has name in caps)
    for line in lines:
        if skip_re.search(line):
            continue
        stripped = re.sub(r'[^A-Za-z\s]', '', line).strip()
        if re.match(r'^[A-Z][A-Z\s]{3,40}$', stripped):
            words = stripped.split()
            if 2 <= len(words) <= 5 and not _JUNK.search(stripped):
                return stripped.title()

    return _after_label(lines, re.compile(r'\bname\b', re.IGNORECASE))


def _passport_name(lines):
    surname = _after_label(lines, re.compile(r'\bsurname\b', re.IGNORECASE))
    given   = _after_label(lines, re.compile(r'\bgiven.name\b', re.IGNORECASE))
    if surname and given:
        return '{} {}'.format(given, surname).title()
    if surname or given:
        return surname or given
    for line in lines:
        if re.match(r'^P<[A-Z]{3}', line):
            parts = line[5:].split('<<')
            sn = parts[0].replace('<', ' ').strip().title()
            gn = parts[1].replace('<', ' ').strip().title() if len(parts) > 1 else ''
            name = '{} {}'.format(gn, sn).strip()
            if _is_name(name):
                return name
    for line in lines:
        if _is_name(line.title()):
            return line.title()
    return ''


def extract_name(doc_type, text):
    # If Surepass OCR already extracted the name, use it directly
    cached = _surepass_name_cache.get('name', '')
    if cached:
        _surepass_name_cache['name'] = ''  # clear after use
        print('[OCR] Using Surepass cached name: {!r}'.format(cached))
        return cached

    ls = _lines(text)
    print('[OCR] doc_type={}, lines={}'.format(doc_type, len(ls)))
    dt = doc_type.lower()
    if 'pan' in dt:
        name = _pan_name(ls)
    elif 'aadhaar' in dt or 'aadhar' in dt:
        name = _aadhaar_name(ls)
    elif 'voter' in dt:
        name = _voter_name(ls)
    elif 'driving' in dt or 'licen' in dt:
        name = _dl_name(ls)
    elif 'passport' in dt:
        name = _passport_name(ls)
    else:
        name = _after_label(ls, re.compile(r'\bname\b', re.IGNORECASE))
        if not name:
            for line in ls:
                if _is_name(line.title()):
                    name = line.title()
                    break
    print('[OCR] Extracted name: {!r}'.format(name))
    return name


# -- Name matching ------------------------------------------------------------

def _similarity(a, b):
    """Simple word-overlap similarity ratio between two name strings."""
    a_words = set(a.lower().split())
    b_words = set(b.lower().split())
    if not a_words or not b_words:
        return 0.0
    overlap = len(a_words & b_words)
    return overlap / max(len(a_words), len(b_words))


def match_names(user_name, doc_name):
    if doc_name in ('__NO_OCR__', '__TESSERACT_MISSING__', ''):
        if doc_name == '__NO_OCR__':
            msg = 'OCR engine not configured. Please enter your name and document number manually below.'
        else:
            msg = "We couldn't read the document clearly. Please re-upload a clearer image or enter details manually."
        return {'status': 'MANUAL', 'message': msg, 'doc_name': ''}

    # Name is mandatory — block verification if not provided
    if not user_name.strip():
        return {'status': 'NAME_REQUIRED',
                'message': 'Please enter your Full Name before verification.',
                'doc_name': doc_name}

    sim = _similarity(user_name, doc_name)
    print('[OCR] Name similarity: {:.2f} ({!r} vs {!r})'.format(sim, user_name, doc_name))

    if sim >= 0.7:
        return {'status': 'VERIFIED',
                'message': 'Document verified successfully. (Name: {})'.format(doc_name),
                'doc_name': doc_name}

    if sim >= 0.4:
        # Partial match — show extracted name and ask user to confirm
        return {'status': 'CONFIRM',
                'message': 'We detected: "{}". Please confirm or correct your full name.'.format(doc_name),
                'doc_name': doc_name}

    return {'status': 'MISMATCH',
            'message': 'Name mismatch - Document shows: "{}". Please check your Full Name field.'.format(doc_name),
            'doc_name': doc_name}
