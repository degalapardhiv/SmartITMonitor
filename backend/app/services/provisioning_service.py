import hashlib
import logging
import os
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)


class ProvisioningError(Exception):
    pass


def verify_image_checksum(image):
    """Verify the recorded checksum against a real image file.

    The image store directory is configured with SMARTIT_IMAGE_DIR.
    Files are stored keyed by their checksum (image store pattern).
    Returns True when the file exists and its checksum matches.
    Raises ProvisioningError when the image cannot be verified.
    """

    image_dir = os.getenv("SMARTIT_IMAGE_DIR", "").strip()

    if not image_dir:
        raise ProvisioningError(
            "Image checksum verification unavailable: "
            "SMARTIT_IMAGE_DIR is not configured"
        )

    checksum = (image.checksum or "").strip()

    if not checksum:
        raise ProvisioningError(
            f"Image {image.name} has no recorded checksum"
        )

    checksum_type = (image.checksum_type or "sha256").lower()

    if checksum_type != "sha256":
        raise ProvisioningError(
            f"Unsupported checksum type: {checksum_type}"
        )

    path = os.path.join(image_dir, checksum)

    if not os.path.isfile(path):
        raise ProvisioningError(
            f"Image file not found in store: {checksum}"
        )

    digest = hashlib.sha256()

    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)

    actual = digest.hexdigest()

    if actual != checksum.lower():
        raise ProvisioningError(
            f"Checksum mismatch for {image.name}: "
            f"expected {checksum}, got {actual}"
        )

    return True


def _pxe_network_device_mac(db, ip):
    try:
        from ..network_device_model import NetworkDevice

        device = (
            db.query(NetworkDevice)
            .filter(NetworkDevice.ip == ip)
            .first()
        )

        if device and device.mac:
            return device.mac

    except Exception:
        pass

    return None


def _pxe_config_payload(deployment, image, mac):
    kernel = image.kernel_path or "/images/vmlinuz"

    initrd = image.initrd_path or "/images/initrd.img"

    append = f"initrd={initrd}"

    if image.kickstart_url:
        append += f" inst.ks={image.kickstart_url}"

    return (
        f"default smartit-{deployment.id}\n"
        f"prompt 0\n"
        f"timeout 5\n"
        f"\n"
        f"label smartit-{deployment.id}\n"
        f"  kernel {kernel}\n"
        f"  append {append}\n"
    )


def provision_pxe_local(db, deployment, image):
    """Write a real pxelinux boot configuration for the target device.

    SMARTIT_PXE_DIR must point at the TFTP server's pxelinux.cfg directory
    (e.g. /srv/tftp/pxelinux.cfg). Files are named 01-<mac> when the MAC is
    known, otherwise by the deployment id.
    """

    pxe_dir = os.getenv("SMARTIT_PXE_DIR", "").strip()

    if not pxe_dir:
        raise ProvisioningError(
            "PXE provisioning not configured: SMARTIT_PXE_DIR is not set"
        )

    if not os.path.isdir(pxe_dir):
        raise ProvisioningError(
            f"PXE directory does not exist: {pxe_dir}"
        )

    mac = _pxe_network_device_mac(db, deployment.ip)

    if mac:
        filename = "01-" + mac.replace(":", "-").lower()
    else:
        filename = f"smartit-deploy-{deployment.id}"

    path = os.path.join(pxe_dir, filename)

    config = _pxe_config_payload(deployment, image, mac)

    try:
        with open(path, "w") as handle:
            handle.write(config)

        os.chmod(path, 0o644)

    except OSError as exc:
        raise ProvisioningError(
            f"Failed to write PXE config {path}: {exc}"
        )

    return {"method": "pxe_local", "config": path}


def provision_api_webhook(deployment, image):
    """Push the deployment to an enterprise provisioning API.

    Configure SMARTIT_PROVISIONING_API_URL and optionally
    SMARTIT_PROVISIONING_API_TOKEN (or the Settings Center
    provisioning section). The endpoint receives the device and
    image details as JSON and is expected to perform the actual OS
    provisioning (PXE boot, imaging, etc.).
    """

    from app.settings_center_service import get_provisioning_config

    config = get_provisioning_config()

    url = config["api_url"]

    if not url:
        raise ProvisioningError(
            "Provisioning API not configured: "
            "SMARTIT_PROVISIONING_API_URL is not set"
        )

    token = config["api_token"]

    headers = {"Content-Type": "application/json"}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {
        "deployment_id": deployment.id,
        "hostname": deployment.hostname,
        "ip": deployment.ip,
        "image": {
            "name": image.name,
            "version": image.version,
            "edition": image.edition,
            "architecture": image.architecture,
            "kernel_path": image.kernel_path,
            "initrd_path": image.initrd_path,
            "kickstart_url": image.kickstart_url,
        },
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=15,
        )

        response.raise_for_status()

    except requests.RequestException as exc:
        raise ProvisioningError(
            f"Provisioning API request failed: {exc}"
        )

    return {"method": "api_webhook", "url": url, "status": response.status_code}


def provision_deployment(db, deployment, image):
    """Hand off a deployment to the configured provisioning system."""

    from app.settings_center_service import get_provisioning_config

    config = get_provisioning_config()

    if config["api_url"]:
        return provision_api_webhook(deployment, image)

    return provision_pxe_local(db, deployment, image)


def deployment_timeout_minutes():
    from app.settings_center_service import get_provisioning_config

    config = get_provisioning_config()

    return max(1, config["deploy_timeout_minutes"])


def install_timeout_reached(deployment):
    timeout = deployment_timeout_minutes()

    if not deployment.created_at:
        return False

    deadline = deployment.created_at + timedelta(minutes=timeout)

    return datetime.utcnow() > deadline