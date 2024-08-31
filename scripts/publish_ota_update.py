import argparse
import json
import logging
import subprocess
from hashlib import sha256
from pathlib import Path
from tomllib import load

PACKAGES_PREFIX = 'mpypi/packages/'

logging.basicConfig(level=logging.INFO)

# Argument parser setup
parser = argparse.ArgumentParser(
    description="Publish OTA update to remote device via MQTT")
parser.add_argument('--device-ids', required=True, nargs='+',
                    help="List of remote device IDs")
parser.add_argument('--extra-src-files', required=False, nargs='*',
                    default=(), type=Path,
                    help="List of extra source files")
parser.add_argument('--dev', action='store_true',
                    help="Include 'dev' in the version string")
args = parser.parse_args()

with open('pyproject.toml', 'rb') as pyproject_f:
    version = load(pyproject_f)['tool']['poetry']['version']

if args.dev:
        version += 'dev'

# Calculate the SHA256 checksum of the package
pkg_path = Path('./dist/mpy_blox-latest-mpy6-bytecode-esp32.whl')
pkg_sha256 = sha256(pkg_path.read_bytes()).hexdigest()
files_to_publish = [(f'wheel/{pkg_sha256}', pkg_path)]

# Create the JSON structure with the update information
update_payload = [
    {
      'name': 'mpy-blox',
      'version': version,
      'type': 'wheel',
      'pkg_sha256': pkg_sha256
    }
]

src_path: Path
for src_path in args.extra_src_files:
    pkg_sha256 = sha256(pkg_path.read_bytes()).hexdigest()
    rel_path = src_path.relative_to('.')
    files_to_publish.append((f'src/{rel_path}/{pkg_sha256}',
                             src_path))
    update_payload.append({
        'path': str(rel_path),
        'type': 'src',
        'pkg_sha256': pkg_sha256
    })

# We publish the MQTT messages for this update using mqttx-cli
# First we send the files, so they are available when the JSON arrives
for pkg_id, pkg_path in files_to_publish:
    logging.info("Publishing %s (%s)", pkg_path, pkg_id)
    with pkg_path.open('rb') as pkg_f:
        subprocess.run(
            [
                'mqttx-cli',
                'pub', '-t', PACKAGES_PREFIX + pkg_id,
                '--retain', '--stdin',
                '--message-expiry-interval', '86400'  # Keep update file for 24h
            ],
            stdin=pkg_f
        )

# Then we distribute the update information to all device IDs
update_json_bytes = json.dumps(update_payload).encode()
device_id: str
for device_id in args.device_ids:
    logging.info("Commanding device %s", device_id)
    subprocess.run(
        [
            'mqttx-cli',
            'pub', '-t', f"mpypi/nodes/{device_id}/cmd",
            '--stdin',
        ],
        input=update_json_bytes
    )

# TODO Add update channels
