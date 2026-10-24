# Optional phone-camera button

Run the wizard with `--phonecam` to install a Waybar on/off button and user service. `android-tools` is included in its dependency group. Install **DroidCam CLI** and the required V4L2 loopback kernel module using [DroidCam's official Linux instructions](https://www.dev47apps.com/droidcam/linux/). These are separate from the rice: the installer does not compile kernel modules, modify Secure Boot, install AUR packages or download proprietary clients automatically.

1. Install the DroidCam phone app and open it.
2. For USB, authorize this computer's ADB connection on your phone.
3. For Wi-Fi, keep the app in the foreground and connect the phone and PC to the same trusted local IPv4 network.
4. Click the Waybar camera button. Click again to stop.

USB uses the first authorized ADB device and forwards TCP 4747. Otherwise the helper tries a cached local address, then probes the active IPv4 `/24` subnet for port 4747. Discovery can take several seconds; networks with client isolation, other subnet sizes or firewalls may need manual configuration. The optional helper does not scan until you explicitly start the camera.

```sh
yorha-phonecam status
yorha-phonecam start
yorha-phonecam stop
journalctl --user -u yorha-phonecam.service
```

The button indicates the DroidCam process/service state, not independent verification of video frames. Confirm the selected video device in your meeting application. The service is on demand and is not enabled at login.
