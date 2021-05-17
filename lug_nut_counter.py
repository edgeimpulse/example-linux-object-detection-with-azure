import os
import asyncio
import cv2
import sys
import signal
import time
import uuid
from edge_impulse_linux.image import ImageImpulseRunner
from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device import Message
import cli_parser

cli_args = cli_parser.parser.parse_args()
# TODO: Remove this
print(cli_args)

runner = None
WHEEL_COLOR = (200, 10, 0)
LUG_NUT_COLOR = (0, 250, 15)

def now():
    return round(time.time() * 1000)

def get_camera() -> int:
    if cli_args.port != None:
        camera = cv2.VideoCapture(cli_args.port)
        ret = camera.read()[0]
        if ret:
            print("Camera found on port {}. Resolution = ({} x {}),\
                    name = '{}'".format(cli_args.port, camera.get(3), camera.get(4),
                    camera.getBackendName()))
            camera.release()
            return cli_args.port
        else:
            raise Exception("Couldn't initialize camera")
        
    ports = []
    for port in range(5):
        camera = cv2.VideoCapture(port)
        if camera.isOpened():
            ret = camera.read()[0]
            if ret:
                print("Camera found on port {}. Resolution = ({} x {}),\
                    name = '{}'".format(port, camera.get(3), camera.get(4),
                    camera.getBackendName()))
                ports.append(port)
            camera.release()
    if len(ports) > 1:
        raise Exception("More than one camera found! Use the -p option.")
    if len(ports) == 0:
        raise Exception("No camera found!")
    return ports[0]

def sigint_handler(sig, frame):
    print('Interrupted')
    if runner:
        runner.stop()
    sys.exit(0)

signal.signal(signal.SIGINT, sigint_handler)

async def main():
    # Fetch the connection string from an enviornment variable or cmd line
    conn_str = cli_args.conn_string if cli_args.conn_string != None \
                else os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
    if conn_str == None:
        raise Exception("No Azure IoT connection string found!")

    print("Running lug nut counter with the following options:\n\
            Model file: {0}\nLug nut count: {1}\nConnection string: {2}\n\n"
            .format(cli_args.model_file, cli_args.count, conn_str))

    # Create instance of the device client using the authentication provider
    device_client = IoTHubDeviceClient.create_from_connection_string(conn_str)

    # Connect the device client.
    await device_client.connect()

    # This function will run when the count is not correct
    async def send_alert(lug_nut_count: int):
        msg = Message("Found {0} missing lug nuts!"
            .format(cli_args.count - lug_nut_count))
        msg.message_id = uuid.uuid4()
        msg.custom_properties["counted"] = lug_nut_count
        msg.content_type = "application/json"

        print("Sending message {} to Azure IoT Hub", msg)
        await device_client.send_message(msg)
        print("Message successfully sent!")
    
    dir_path = os.path.dirname(os.path.realpath(__file__))
    modelfile = os.path.join(dir_path, cli_args.model_file)

    with ImageImpulseRunner(modelfile) as runner:
        try:
            model_info = runner.init()
            project_info = model_info['project']
            print("Loaded model for {}/{}".format(project_info['owner'], 
                project_info['name']))
            labels = model_info['model_parameters']['labels']
            print(f"Labels: {labels}")

            capture_device = get_camera()
            
            next_frame = 0

            for res, img in runner.classifier(capture_device):
                if next_frame > now():
                    time.sleep((next_frame - now()) / 1000)
                    
                if "bounding_boxes" in res['result'].keys():
                    found_lug_nuts = 0
                    found_wheel = False
                    for bb in res['result']['bounding_boxes']:
                        print(f"Found {bb['label']} ({bb['value']: 0.2f}) at\
                            x={bb['x']}, y={bb['y']}, w={bb['width']}, h={bb['height']}")

                        if bb['label'] == 'lug_nut':
                            found_lug_nuts += 1
                        elif bb['label'] == 'wheel':
                            found_wheel = True

                        if cli_args.show_cam:
                            label = bb['label']
                            color = WHEEL_COLOR if label == 'wheel' else LUG_NUT_COLOR

                            cv2.rectangle(img, (bb['x'], bb['y']), 
                                (bb['x'] + bb['width'], bb['y'] + bb['height']),
                                color, 2)
                            cv2.putText(img, bb['label'], (bb['x'], bb['y'] + bb['height'] + 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (20, 240, 80), 2)

                            cv2.imshow('Camera', img)
                            if cv2.waitKey(1) == ord('q'):
                                raise KeyboardInterrupt("Exited")

                    # Send a message if the count is wrong
                    if found_lug_nuts < cli_args.count and found_wheel == True:
                        await send_alert(found_lug_nuts)

                # 20 fps max
                next_frame = now() + 50

        finally:
            if runner: 
                runner.stop()
            if device_client.connected():
                await device_client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
