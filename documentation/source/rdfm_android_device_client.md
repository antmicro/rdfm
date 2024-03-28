# RDFM Android Device Client

## Introduction

The RDFM Android Device Client allows for integrating an Android-based device with the RDFM server.
Currently, only OTA update functionality is implemented.

## Integrating the app

This app is **not meant to be built separately** (i.e in Android Studio), but as part of the source tree for an existing device.
The app integrates with the Android UpdateEngine to perform the actual update installation, which requires it to be a system app.
Some configuration is required to the existing system sources.

### Copying the sources

First, copy the sources of the app to the root directory of the AOSP source tree.
After cloning this repository, run the following:
```
mkdir -v -p <path-to-aosp-tree>/vendor/antmicro/rdfm
cd devices/android-client/
cp -r app/src/main/* <path-to-aosp-tree>
```

### Configuring the device Makefile

The [product Makefile](https://source.android.com/docs/setup/create/new-device#build-a-product) must be configured to build the RDFM app into the system image.
To do this, add `rdfm` to the `PRODUCT_PACKAGES` variable in the target device Makefile:
```
PRODUCT_PACKAGES += rdfm
```

### Building the app

Afterwards, [the usual Android build procedure](https://source.android.com/docs/setup/build/building) can be used to build just the app.
From an already configured build environment, run:
```
mma rdfm
```
The resulting signed APK is in `out/target/product/<product-name>/system/app/rdfm/rdfm.apk`.

### Using HTTPS for server requests

The default Android system CA certificates are used when validating the certificate presented by the server.
If the RDFM server that is configured in the app uses a certificate that is signed by a custom Certificate Authority, the CA certificate must be added to the system roots.

## System versioning

The app performs update check requests to the configured RDFM server.
The build version and device type are retrieved from the system properties:
- `ro.build.version.incremental` - the current software version (matches `rdfm.software.version`)
- `ro.build.product` - device type (matches `rdfm.hardware.devtype`)

When uploading an OTA package to the RDFM server, currently these values must be **manually** extracted from the update package, and passed as arguments to `rdfm-mgmt`:
```
rdfm-mgmt packages upload --path ota.zip --version <ro.build.version.incremental> --device <ro.build.product>
```

You can extract the values from the [package metadata file](https://source.android.com/docs/core/ota/tools#ota-package-metadata) by unzipping the OTA package.

## Configuring the app

The application will automatically start on system boot.
Available configuration options are shown below.

### Build-time app configuration

The default build-time configuration can be modified by providing a custom `conf.xml` file in the `app/src/main/res/values/` folder, similar to the one shown below:

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
<!--
    This is an example overlay configuration file for the RDFM app.
    To modify the default server address, you can do:

        <string name="default_rdfm_server_address">http://rdfm.example.local:6000/</string>

    Likewise, overlaying the default update check interval can be done similarly:

        <string name="default_update_check_interval_seconds">240</string>

    NOTE: These settings are only used during the app's first startup. To change them afterwards,
    you must delete the existing configuration file.
-->
</resources>
```

This build-time configuration is applied **only once, at first startup of the app**, as the main use case for this is first-time configuration for newly provisioned devices.
Modifying it afterwards (for example, via an update containing a new version of the RDFM app) will not result in the change of existing configuration.

### Runtime app configuration

It is possible to change the app's configuration at runtime by simply starting the RDFM app from the drawer and selecting `Settings` from the context menu.

### Configuration options

The following configuration options are available:
- RDFM server URL (`http`/`https` scheme)
- Update check interval (in seconds)
- Maximum amount of concurrent shell sessions (set to `0` to disable reverse shell functionality)

## Available intents

### Update check intent

This intent allows an external app to force perform an update check outside of the usual automatic update check interval.
To do this, the app that wants to perform the update check must have the `com.antmicro.update.rdfm.permission.UPDATE_CHECK` permission defined in its `AndroidManifest.xml` file:

```xml
<uses-permission android:name="com.antmicro.update.rdfm.permission.UPDATE_CHECK" />
```

Afterwards, an update check can then be forced like so:
```java
Intent configIntent = new Intent("com.antmicro.update.rdfm.startUpdate");
mContext.sendBroadcast(configIntent);
```

### External configuration via intents

The app settings can also be configured via intents, for example in order to change between different deployment environments.
To do this, the app that performs the configuring step must have the `com.antmicro.update.rdfm.permission.CONFIGURATION` permission defined in its `AndroidManifest.xml` file:
```xml
<uses-permission android:name="com.antmicro.update.rdfm.permission.CONFIGURATION" />
```

To configure the app, use the `com.antmicro.update.rdfm.configurationSet` intent and set extra values on the intent to the settings you wish to change.
For example, to set the server address:
```java
Intent configIntent = new Intent("com.antmicro.update.rdfm.configurationSet");
configIntent.putExtra("ota_server_address", "http://CUSTOM-OTA-ADDRESS/");
mContext.sendBroadcast(configIntent);
```

The supported configuration key names can be found in the `res/values/strings.xml` file with the `preference_` prefix.

Aside from setting the configuration, you can also fetch the current configuration of the app:
```java
Intent configIntent = new Intent("com.antmicro.update.rdfm.configurationGet");
mContext.sendBroadcast(configIntent);

// Now listen for `com.antmicro.update.rdfm.configurationResponse` broadcast intent
// The intent's extras bundle will contain the configuration keys and values
```

## Development

The provided Gradle files can be used for development purposes, simply open the `devices/android-client` directory in Android Studio.
Missing references to the `UpdateEngine` class are expected, but they do not prevent regular use of the IDE.

Do note however that **the app is not buildable from Android Studio**, as it requires integration with the aforementioned system API.
To test the app, an existing system source tree must be used.
Copy the modified sources to the AOSP tree, and re-run the [application build](#building-the-app).
The modified APK can then be uploaded to the device via ADB by running:
```
adb install <path-to-rdfm.apk>
```

### Restarting the app

With the target device connected via ADB, run:
```
adb shell am force-stop com.antmicro.update.rdfm
adb shell am start -n com.antmicro.update.rdfm/.MainActivity
```

### Fetching app logs

To view the application logs, run:
```
adb logcat --pid=`adb shell pidof -s com.antmicro.update.rdfm`
```
