# Linux Object Detection Example with Azure IoT

- [Linux Object Detection Example with Azure IoT](#linux-object-detection-example-with-azure-iot)
  - [Overview](#overview)
  - [Configuring the Raspberry Pi 4](#configuring-the-raspberry-pi-4)
  - [Data Capture and Model Training](#data-capture-and-model-training)
    - [Capture](#capture)
    - [Training](#training)
    - [Testing](#testing)
  - [Azure IoT Hub Setup](#azure-iot-hub-setup)
    - [Azure installations and creation](#azure-installations-and-creation)
    - [Running the model locally](#running-the-model-locally)
  - [Running the Application](#running-the-application)
  - [Wrapping Up](#wrapping-up)

## Overview

This project is meant to be a guide for quickly getting started with Edge Impulse on a Raspberry Pi 4 to train a model that detects lug nuts on a wheel and sends alerts to the Azure IoT Hub service if some are missing.

## Configuring the Raspberry Pi 4

To begin, you’ll need a Raspberry Pi 4 with an up-to-date Raspberry Pi OS image that can be found here. After flashing this image to an SD card and adding a file named `wpa_supplicant.conf`:

```text
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=<Insert 2 letter ISO 3166-1 country code here>

network={
 ssid="<Name of your wireless LAN>"
 psk="<Password for your wireless LAN>"
}
```

along with an empty file named `ssh` (both within the `/boot` directory), you can go ahead and power up the board. Once you’ve successfully SSH’d into the device with `ssh pi@<IP_ADDRESS>` and the password `raspberry`, it’s time to install the dependencies for the Edge Impulse Linux Wizard. Simply run the next three commands to set up the NodeJS environment and everything else that’s required for the edge-impulse-linux wizard:

```bash
$ curl -sL https://deb.nodesource.com/setup_12.x | sudo bash -

$ sudo apt install -y gcc g++ make build-essential nodejs sox gstreamer1.0-tools gstreamer1.0-plugins-good gstreamer1.0-plugins-base gstreamer1.0-plugins-base-apps

$ npm config set user root && sudo npm install edge-impulse-linux -g --unsafe-perm
```

Since this project deals with images, we’ll need some way to capture them. The wizard supports both the Pi camera modules and standard USB webcams, so make sure to enable the camera module first with

```bash
$ sudo raspi-config
```

if you plan on using one. With that completed, go to the [Edge Impulse Studio](https://studio.edgeimpulse.com/studio/select-project) and create a new project, then run the wizard with

```bash
$ edge-impulse-linux
```

and make sure your device appears within the Edge Impulse Studio’s device section after logging in and selecting your project.

## Data Capture and Model Training

### Capture

For this use case, I captured around 50 images of a wheel that had lug nuts on it. After I was done, I headed to the Labeling queue in the Data Acquisition page and added bounding boxes around each lug nut within every image, along with every wheel. To add some test data I went back to the main Dashboard page and clicked the `Rebalance dataset` button that moves 20% of the training data to the test data bin.

### Training

The first block in the impulse is an Image Data block, and it scales each image to a size of `320` by `320` pixels. Next, image data is fed to the Image processing block that takes the raw RGB data and derives features from it. Finally, these features are sent to the Transfer Learning Object Detection model that learns to recognize the objects. I set my model to train for `30` cycles at a learning rate of `.15`, but this can be adjusted to fine-tune the accuracy.

### Testing

In order to verify that the model works correctly in the real world, we’ll need to deploy it to the Raspberry Pi 4. This is a simple task thanks to the Edge Impulse CLI, as all we have to do is run

```bash
$ edge-impulse-linux-runner
```

which downloads the model and creates a local webserver. From here, we can open a browser tab and visit the address listed after we run the command to see a live camera feed and any objects that are currently detected.

## Azure IoT Hub Setup

### Azure installations and creation

With the model working locally on the device, let’s add an integration with an Azure IoT Hub that will allow the Pi to send messages to the cloud. First, make sure you’ve installed the [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest) and have signed in using

```bash
$ az login
```

Then, get the name of the resource group you’ll be using for the project. If you don’t have one, you can [follow this guide](https://docs.microsoft.com/en-us/azure/azure-resource-manager/management/manage-resource-groups-portal) on how to create a new resource group. After that, return to the terminal and run the following commands to create a new IoT Hub and register a new device ID:

```bash
$ az iot hub create --resource-group <your resource group> --name <your IoT Hub name>

$ az extension add --name azure-iot

$ az iot hub device-identity create --hub-name <your IoT Hub name> --device-id <your device id>
```

Retrieve the connection string with

```bash
$ az iot hub device-identity connection-string show --device-id <your device id> --hub-name <your IoT Hub name>
``` 

and set it as an environment variable with

```bash
$ export IOTHUB_DEVICE_CONNECTION_STRING="<your connection string here>"
```

in the Pi’s SSH session. Run:

```bash
$ pip3 install azure-iot-device
```

to add the necessary libraries. (Note: if you do not set the environment variable or pass it in as an argument the program will not work!) The connection string contains the information required for the device to establish a connection with the IoT Hub service and communicate with it. You can monitor output in the Hub with

```bash
$ az iot hub monitor-events --hub-name <your IoT Hub name> --output table
```

or in the Azure Portal. To make sure it works, [download and run this example](https://github.com/Azure/azure-iot-sdk-python/blob/master/azure-iot-device/samples/simple_send_message.py) to make sure you can see the test message.

### Running the model locally

For the second half of deployment, we’ll need a way to customize how our model is used within the code. Thankfully, Edge Impulse provides a Python SD. Install it with
```bash
$ sudo apt-get install libatlas-base-dev libportaudio0 libportaudio2 libportaudiocpp0 portaudio19-dev

$ pip3 install edge_impulse_linux -i https://pypi.python.org/simple
```

## Running the Application

There’s [some simple code that can be found here on Github](https://github.com/edgeimpulse/linux-object-detection-azure), and it works by setting up a connection to the Azure IoT Hub and then running the model. You can [view the public Edge Impulse project for this example here](https://studio.edgeimpulse.com/public/33006/latest).

Once you’ve either downloaded the zip file or cloned the repo into a folder, get the model file by running

```bash
$ edge-impulse-linux-runner --download modelfile.eim
```

inside of the folder you just created from the cloning process. This will download a file called `modelfile.eim`. Now, run the Python program with

```bash
$ python lug_nut_counter.py ./modelfile.eim -c <LUG_NUT_COUNT>
```

where `<LUG_NUT_COUNT>` is the correct number of lug nuts that should be attached to the wheel (you might have to use `python3` if both Python 2 and 3 are installed). There are several other flags that can be set to control things like viewing camera output + bounding boxes and the camera port, so just run

```bash
$ python lug_nut_counter.py -h
```

for more information.

Now whenever a wheel is detected, the number of lug nuts is calculated. If this number falls short of the target, a message is sent to the Azure IoT Hub. By only sending messages when there’s something wrong, we can prevent an excess amount of bandwidth from being taken due to empty payloads.

## Wrapping Up

Feel free to train your own model to detect other things. You can also try integrating various Azure services into your project such as Functions or Hooks.
