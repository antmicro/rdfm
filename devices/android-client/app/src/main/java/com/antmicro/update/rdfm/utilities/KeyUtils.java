package com.antmicro.update.rdfm.utilities;

import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.InvalidAlgorithmParameterException;
import java.security.InvalidKeyException;
import java.security.KeyPairGenerator;
import java.security.KeyStore;
import java.security.KeyStoreException;
import java.security.NoSuchAlgorithmException;
import java.security.PublicKey;
import java.security.Signature;
import java.security.SignatureException;
import java.security.UnrecoverableEntryException;
import java.security.cert.CertificateException;
import java.util.Base64;

public class KeyUtils {
    private static final String TAG = "KeyUtils";
    private static final String keyStoreAlias = "rdfm_device_key";

    private static KeyStore loadKeyStore() {
        try {
            KeyStore keyStore = KeyStore.getInstance("AndroidKeyStore");
            keyStore.load(null);
            return keyStore;
        } catch (KeyStoreException | CertificateException | IOException | NoSuchAlgorithmException e) {
            throw new RuntimeException(e);
        }
    }

    private static KeyStore.Entry generateKeyIfNotExist(KeyStore keyStore) {
        try {
            KeyStore.Entry entry = keyStore.getEntry(keyStoreAlias, null);
            if (!(entry instanceof KeyStore.PrivateKeyEntry))
                generateAndStoreKeyPair();
            return entry;
        } catch (KeyStoreException | NoSuchAlgorithmException | UnrecoverableEntryException e) {
            throw new RuntimeException(e);
        }
    }

    public static String getPublicKey() {
        try {
            KeyStore keyStore = loadKeyStore();
            generateKeyIfNotExist(keyStore);
            PublicKey pubKey =  keyStore.getCertificate(keyStoreAlias).getPublicKey();
            String pubKeyBase64 = android.util.Base64.encodeToString(pubKey.getEncoded(), android.util.Base64.DEFAULT);
            return "-----BEGIN PUBLIC KEY-----\n" + pubKeyBase64 + "-----END PUBLIC KEY-----";
        } catch (KeyStoreException e) {
            throw new RuntimeException(e);
        }
    }

    private static void generateAndStoreKeyPair() {
        try {
            KeyPairGenerator keyPairGen = KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_RSA);

            KeyGenParameterSpec keyGenParameterSpec = new KeyGenParameterSpec.Builder(
                    keyStoreAlias, KeyProperties.PURPOSE_SIGN | KeyProperties.PURPOSE_VERIFY)
                    .setDigests(KeyProperties.DIGEST_SHA256)
                    .setSignaturePaddings(KeyProperties.SIGNATURE_PADDING_RSA_PKCS1)
                    .setKeySize(4096)
                    .build();

            keyPairGen.initialize(keyGenParameterSpec);
            keyPairGen.generateKeyPair();
        } catch (NoSuchAlgorithmException | InvalidAlgorithmParameterException e) {
            throw new RuntimeException(e);
        }
    }

    public static String signData(String reqJSON) {
        KeyStore keyStore = loadKeyStore();
        KeyStore.Entry entry = generateKeyIfNotExist(keyStore);
        try {
            Signature signature = Signature.getInstance("SHA256withRSA");
            signature.initSign(((KeyStore.PrivateKeyEntry) entry).getPrivateKey());
            signature.update(reqJSON.getBytes(StandardCharsets.UTF_8));
            byte[] sign = signature.sign();
            return Base64.getEncoder().encodeToString(sign);
        } catch (NoSuchAlgorithmException | InvalidKeyException | SignatureException e) {
            throw new RuntimeException(e);
        }
    }

}
