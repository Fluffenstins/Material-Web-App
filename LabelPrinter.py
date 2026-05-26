from niimprint import PrinterClient, SerialTransport, BluetoothTransport
import serial
from PIL import Image


def print_image(path="label.png"):
    port = get_niimbot_port()
    # 1. Set up the transport (Change 'COM3' or '/dev/ttyACM0' to your port)
    transport = SerialTransport(port)

    # 2. Initialize the printer (e.g., B21, B1, or D11)
    printer = PrinterClient(transport)

    # 3. Open your image (must be the correct size for your labels)
    img = Image.open(path)

    # 4. Print!
    # 'density' (1-3) and 'quantity' can be adjusted
    printer.print_image(img, density=3)


def get_niimbot_port():
    ports = serial.tools.list_ports.comports()

    correct_port = None
    for port in sorted(ports):
        desc = port.description.lower()
        if desc.find('niimbot') == -1:
            continue
        correct_port = port

    if correct_port is None:
        raise AttributeError("Port not found for Niimbot, please ensure that it is plugged in.")

    return correct_port.device
