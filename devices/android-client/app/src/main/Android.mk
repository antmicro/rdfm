LOCAL_PATH:= $(call my-dir)
include $(CLEAR_VARS)

LOCAL_PACKAGE_NAME := rdfm
LOCAL_CERTIFICATE := platform
LOCAL_PRIVATE_PLATFORM_APIS := true

LOCAL_SRC_FILES := \
    $(call all-java-files-under, java/com/antmicro/update/rdfm/) \

LOCAL_STATIC_JAVA_LIBRARIES := \
    guava \
    androidx.appcompat_appcompat \
    androidx.preference_preference \
    okhttp-4.11.0 \
    okio-3.2.0 \
    okio-jvm-3.2.0 \
    annotations-13.0 \
    logging-interceptor-4.11.0 \
    kotlin-stdlib-1.6.20 \
    kotlin-stdlib-common-1.6.20 \
    kotlin-stdlib-jdk7-1.6.10 \
    kotlin-stdlib-jdk8-1.6.10 \
    conscrypt-openjdk-uber-2.5.2 \
    bcpkix-jdk18on-1.76 \
    bcprov-jdk18on-1.76 \
    bcutil-jdk18on-1.76 \

include $(BUILD_PACKAGE)

include $(CLEAR_VARS)

LOCAL_PREBUILT_STATIC_JAVA_LIBRARIES := \
    okhttp-4.11.0:libs/okhttp-4.11.0.jar \
    okio-3.2.0:libs/okio-3.2.0.jar \
    okio-jvm-3.2.0:libs/okio-jvm-3.2.0.jar \
    annotations-13.0:libs/annotations-13.0.jar \
    logging-interceptor-4.11.0:libs/logging-interceptor-4.11.0.jar \
    kotlin-stdlib-1.6.20:libs/kotlin-stdlib-1.6.20.jar \
    kotlin-stdlib-common-1.6.20:libs/kotlin-stdlib-common-1.6.20.jar \
    kotlin-stdlib-jdk7-1.6.10:libs/kotlin-stdlib-jdk7-1.6.10.jar \
    kotlin-stdlib-jdk8-1.6.10:libs/kotlin-stdlib-jdk8-1.6.10.jar \
    conscrypt-openjdk-uber-2.5.2:libs/conscrypt-openjdk-uber-2.5.2.jar \
    bcpkix-jdk18on-1.76:libs/bcpkix-jdk18on-1.76.jar \
    bcprov-jdk18on-1.76:libs/bcprov-jdk18on-1.76.jar \
    bcutil-jdk18on-1.76:libs/bcutil-jdk18on-1.76.jar \

include $(BUILD_MULTI_PREBUILT)
