package com.antmicro.update.rdfm.utilities;

import android.content.Context;
import android.util.Log;

import org.bouncycastle.asn1.x500.X500Name;
import org.bouncycastle.asn1.x509.AlgorithmIdentifier;
import org.bouncycastle.asn1.x509.SubjectPublicKeyInfo;
import org.bouncycastle.cert.X509CertificateHolder;
import org.bouncycastle.cert.X509v3CertificateBuilder;
import org.bouncycastle.cert.jcajce.JcaX509CertificateConverter;
import org.bouncycastle.crypto.params.AsymmetricKeyParameter;
import org.bouncycastle.crypto.util.PrivateKeyFactory;
import org.bouncycastle.operator.ContentSigner;
import org.bouncycastle.operator.DefaultDigestAlgorithmIdentifierFinder;
import org.bouncycastle.operator.DefaultSignatureAlgorithmIdentifierFinder;
import org.bouncycastle.operator.OperatorCreationException;
import org.bouncycastle.operator.bc.BcRSAContentSignerBuilder;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.security.InvalidKeyException;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.KeyStore;
import java.security.KeyStoreException;
import java.security.NoSuchAlgorithmException;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.SecureRandom;
import java.security.Signature;
import java.security.SignatureException;
import java.security.UnrecoverableEntryException;
import java.security.UnrecoverableKeyException;
import java.security.cert.Certificate;
import java.security.cert.CertificateException;
import java.security.cert.X509Certificate;
import java.util.Base64;
import java.util.Calendar;

public class KeyUtils {
    private static final String TAG = "KeyUtils";
    private static final String keyStoreFilename = "rdfm_keystore";
    private static final String keyStoreAlias = "rdfm_device_key";
    private static final char[] keyStorePassword = "RDFM_KEYSTORE_PASSWORD".toCharArray();
    private static final int rsaDeviceKeySize = 4096;

    private static KeyStore loadKeyStoreFromFile(File keyStoreFile, char[] keyStorePassword) {
        try {
            KeyStore keyStore = KeyStore.getInstance(KeyStore.getDefaultType());
            try (FileInputStream fileInputStream = new FileInputStream(keyStoreFile)) {
                keyStore.load(fileInputStream, keyStorePassword);
            }
            return keyStore;
        } catch (KeyStoreException | IOException | CertificateException |
                 NoSuchAlgorithmException e) {
            throw new RuntimeException("Failed to load keystore from file. " +
                                       "An invalid password may have been configured for unlocking the RDFM key store; " +
                                       "please verify if the configured password matches the one used during key store creation.", e);
        }
    }

    private static void storeKeyStoreToFile(KeyStore keyStore, File keyStoreFile, char[] keyStorePassword) {
        try {
            try (FileOutputStream fileOutputStream = new FileOutputStream(keyStoreFile)) {
                keyStore.store(fileOutputStream, keyStorePassword);
            }
        } catch (IOException | CertificateException | KeyStoreException |
                 NoSuchAlgorithmException e) {
            throw new RuntimeException("Failed to store keystore to file", e);
        }
    }

    private static KeyStore loadOrGenerateKeyStore(File keyStoreFile, char[] keyStorePassword) {
        try {
            KeyStore keyStore;
            if (keyStoreFile.exists()) {
                Log.d(TAG, "RDFM key store exists, loading from file: " + keyStoreFile.getAbsolutePath());
                keyStore = loadKeyStoreFromFile(keyStoreFile, keyStorePassword);
                // Generate a device key if one is not present in the loaded keystore
                if (!keyStore.containsAlias(keyStoreAlias)) {
                    Log.d(TAG, "RDFM key store does not contain a device key, generating");
                    generateDeviceKey(keyStore);
                    storeKeyStoreToFile(keyStore, keyStoreFile, keyStorePassword);
                }
            } else {
                Log.d(TAG, "RDFM key store not found, generating..");
                keyStore = KeyStore.getInstance(KeyStore.getDefaultType());
                keyStore.load(null, null);
                // Immediately generate the device key
                generateDeviceKey(keyStore);
                storeKeyStoreToFile(keyStore, keyStoreFile, keyStorePassword);
            }
            return keyStore;
        } catch (KeyStoreException | CertificateException | IOException |
                 NoSuchAlgorithmException e) {
            throw new RuntimeException("Failed to instantiate the RDFM keystore", e);
        }
    }

    private static KeyStore loadKeyStore(Context context) {
        File storeFile = new File(context.getFilesDir(), keyStoreFilename);
        return loadOrGenerateKeyStore(storeFile, keyStorePassword);
    }

    // In order to store the private/public key pair, the KeyStore abstraction requires
    // that the public key is formatted as an X.509 certificate, even if we don't need one otherwise.
    // This generates the required self-signed certificate for a generated RSA key pair.
    private static X509Certificate selfSignRsaKeyPair(KeyPair keyPair) {
        try {
            AlgorithmIdentifier sigAlgId = new DefaultSignatureAlgorithmIdentifierFinder().find("SHA256withRSA");
            AlgorithmIdentifier digAlgId = new DefaultDigestAlgorithmIdentifierFinder().find(sigAlgId);

            AsymmetricKeyParameter keyParam = PrivateKeyFactory.createKey(keyPair.getPrivate().getEncoded());
            SubjectPublicKeyInfo spki = SubjectPublicKeyInfo.getInstance(keyPair.getPublic().getEncoded());
            ContentSigner signer = new BcRSAContentSignerBuilder(sigAlgId, digAlgId).build(keyParam);

            // Below values are irrelevant
            // They are required for generating the certificate and must be present
            // We don't use any of the X.509 fields, but the keystore requires that
            // a certificate is used for storing the RSA key pair.
            X500Name issuer = new X500Name("CN=RDFM-Android-Client");
            X500Name subject = new X500Name("CN=RDFM-Android-Client");
            BigInteger serial = BigInteger.valueOf(1);
            Calendar notBefore = Calendar.getInstance();
            Calendar notAfter = Calendar.getInstance();
            notAfter.add(Calendar.YEAR, 20);

            X509v3CertificateBuilder v3CertGen = new X509v3CertificateBuilder(issuer,
                    serial,
                    notBefore.getTime(),
                    notAfter.getTime(),
                    subject,
                    spki);
            X509CertificateHolder certificateHolder = v3CertGen.build(signer);
            return new JcaX509CertificateConverter().getCertificate(certificateHolder);
        } catch (IOException | CertificateException | OperatorCreationException e) {
            throw new RuntimeException("Failed to self-sign certificate for storing the device key", e);
        }
    }

    private static void generateDeviceKey(KeyStore keyStore) {
        try {
            KeyPairGenerator generator = KeyPairGenerator.getInstance("RSA");
            generator.initialize(rsaDeviceKeySize, new SecureRandom());
            KeyPair keyPair = generator.generateKeyPair();

            Certificate certificate = selfSignRsaKeyPair(keyPair);
            Certificate[] chain = new Certificate[]{certificate};
            keyStore.setKeyEntry(keyStoreAlias, keyPair.getPrivate(), null, chain);
        } catch (NoSuchAlgorithmException | KeyStoreException e) {
            throw new RuntimeException("Failed to generate device RSA key pair", e);
        }
    }

    private static PrivateKey getDevicePrivateKey(KeyStore keyStore) {
        try {
            if (!keyStore.containsAlias(keyStoreAlias)) {
                generateDeviceKey(keyStore);
            }
            KeyStore.Entry entry = keyStore.getEntry(keyStoreAlias, null);
            KeyStore.PrivateKeyEntry privateKeyEntry = (KeyStore.PrivateKeyEntry) entry;
            return privateKeyEntry.getPrivateKey();
        } catch (KeyStoreException | NoSuchAlgorithmException | UnrecoverableEntryException e) {
            throw new RuntimeException("Failed to get the RDFM device key", e);
        }
    }

    private static PublicKey getDevicePublicKey(KeyStore keyStore) {
        try {
            if (!keyStore.containsAlias(keyStoreAlias)) {
                generateDeviceKey(keyStore);
            }
            return keyStore.getCertificate(keyStoreAlias).getPublicKey();
        } catch (KeyStoreException e) {
            throw new RuntimeException("Failed to get the RDFM device certificate", e);
        }
    }

    public static String getPublicKey(Context context) {
        KeyStore keyStore = loadKeyStore(context);
        PublicKey pubKey = getDevicePublicKey(keyStore);
        String pubKeyBase64 = android.util.Base64.encodeToString(pubKey.getEncoded(), android.util.Base64.DEFAULT);
        return "-----BEGIN PUBLIC KEY-----\n" + pubKeyBase64 + "-----END PUBLIC KEY-----";
    }

    public static String signData(Context context, String reqJSON) {
        KeyStore keyStore = loadKeyStore(context);
        PrivateKey privateKey = getDevicePrivateKey(keyStore);
        try {
            Signature signature = Signature.getInstance("SHA256withRSA");
            signature.initSign(privateKey);
            signature.update(reqJSON.getBytes(StandardCharsets.UTF_8));
            byte[] sign = signature.sign();
            return Base64.getEncoder().encodeToString(sign);
        } catch (NoSuchAlgorithmException | InvalidKeyException | SignatureException e) {
            throw new RuntimeException("Failed to sign request data", e);
        }
    }

}
