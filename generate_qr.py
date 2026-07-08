"""Generate a QR code for the survey URL and save as PNG.

Usage:
    python generate_qr.py                          # auto-detect URL
    python generate_qr.py https://my-url.com       # specify URL manually
"""
import sys
import socket
import qrcode
from pathlib import Path

HERE = Path(__file__).parent

# Determine URL
if len(sys.argv) > 1:
    url = sys.argv[1]
else:
    # Try to detect public URL from localtunnel or cloudflared
    # Default to LAN IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.254.254.254', 1))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = 'localhost'
    url = f'http://{local_ip}:5000'

print(f'Survey URL: {url}')

# Generate QR code
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_M,
    box_size=10,
    border=2,
)
qr.add_data(url)
qr.make(fit=True)

img = qr.make_image(fill_color='#1a1a2e', back_color='white')

out = HERE / 'survey_qr.png'
img.save(out)
print(f'QR code saved to: {out}')
print(f'Public URL (for sharing): {url}')
