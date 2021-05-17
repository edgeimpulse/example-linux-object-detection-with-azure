import argparse

parser = argparse.ArgumentParser()

requiredArgs = parser.add_argument_group('required arguments')

requiredArgs.add_argument('model_file',
                    metavar='PATH',
                    help='Model file path (by default is modelfile.eim)',
                    type=str,
                    nargs=1
                    )

parser.add_argument('-c', '--count-target',
                    default=6,
                    dest='count',
                    metavar='COUNT',
                    type=int,
                    help='The proper number of lug nuts to check against'
                    )

parser.add_argument('-s', '--connection-string',
                    default=None,
                    dest='conn_string',
                    metavar='CONNECTION_STRING',
                    type=str,
                    help='Azure IoT Device connection string; can also be set \
                        in the IOTHUB_DEVICE_CONNECTION_STRING environment variable'
                    )

parser.add_argument('-p', '--camera-port',
                    dest='port',
                    metavar='PORT',
                    type=int,
                    help='Camera port (only needed if multiple cameras are attached'
                    )

parser.add_argument('-d', '--display-camera',
                    dest='show_cam',
                    action='store_true',
                    default=False,
                    help='Show the camera\'s output'
                    )
                    