import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyStore;
import java.security.MessageDigest;
import java.security.PrivateKey;
import java.security.Signature;
import java.security.cert.X509Certificate;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.jar.Attributes;
import java.util.jar.Manifest;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import java.util.zip.ZipOutputStream;

/** Standard-JDK-only, fixed-time v1 signing. Private key material is never exported. */
public class V42Reproducible {
    static byte[] concat(byte[]... parts) {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        for (byte[] part : parts) out.writeBytes(part);
        return out.toByteArray();
    }

    static byte[] der(int tag, byte[] body) {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        out.write(tag);
        if (body.length < 128) {
            out.write(body.length);
        } else {
            int count = (32 - Integer.numberOfLeadingZeros(body.length) + 7) / 8;
            out.write(128 | count);
            for (int shift = (count - 1) * 8; shift >= 0; shift -= 8) out.write(body.length >>> shift);
        }
        out.writeBytes(body);
        return out.toByteArray();
    }

    static byte[] seq(byte[]... values) { return der(0x30, concat(values)); }
    static byte[] oid(String hex) { return der(6, HexFormat.of().parseHex(hex)); }
    static byte[] sha256Algorithm() { return seq(oid("608648016503040201"), der(5, new byte[0])); }
    static byte[] rsaSha256Algorithm() { return seq(oid("2a864886f70d01010b"), der(5, new byte[0])); }
    static byte[] digest(byte[] data) throws Exception { return MessageDigest.getInstance("SHA-256").digest(data); }
    static String hexDigest(byte[] data) throws Exception { return HexFormat.of().formatHex(digest(data)); }
    static String b64Digest(byte[] data) throws Exception { return Base64.getEncoder().encodeToString(digest(data)); }

    static byte[] sortedSet(byte[]... items) {
        Arrays.sort(items, Arrays::compareUnsigned);
        return der(0x31, concat(items));
    }

    static byte[] attribute(String oidHex, byte[] value) { return seq(oid(oidHex), sortedSet(value)); }

    static byte[] signedAttributes(byte[] signatureFile, Instant signingTime) throws Exception {
        String utc = DateTimeFormatter.ofPattern("yyMMddHHmmss'Z'").withZone(ZoneOffset.UTC).format(signingTime);
        byte[] signatureAlgorithm = rsaSha256Algorithm();
        signatureAlgorithm[0] = (byte) 0xa1; // CMSAlgorithmProtection's IMPLICIT [1].
        return sortedSet(
            attribute("2a864886f70d010903", oid("2a864886f70d010701")),
            attribute("2a864886f70d010905", der(0x17, utc.getBytes(StandardCharsets.US_ASCII))),
            attribute("2a864886f70d010934", seq(sha256Algorithm(), signatureAlgorithm)),
            attribute("2a864886f70d010904", der(4, digest(signatureFile)))
        );
    }

    static List<String[]> layout(Path path) throws Exception {
        List<String[]> entries = new ArrayList<>();
        for (String line : Files.readAllLines(path, StandardCharsets.UTF_8)) {
            String[] fields = line.split("\t", -1);
            if (fields.length != 3) throw new IllegalArgumentException("invalid layout row");
            entries.add(fields);
        }
        return entries;
    }

    static byte[] serialize(Manifest manifest) throws Exception {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        manifest.write(out);
        return out.toByteArray();
    }

    static int sectionEnd(byte[] data, int start) {
        for (int i = start; i + 3 < data.length; i++) {
            if (data[i] == 13 && data[i + 1] == 10 && data[i + 2] == 13 && data[i + 3] == 10) return i + 4;
        }
        throw new IllegalArgumentException("unterminated manifest section");
    }

    static String sectionName(byte[] section) {
        ByteArrayOutputStream name = new ByteArrayOutputStream();
        int i = 6; // "Name: "; manifest serialization puts this first.
        while (i < section.length) {
            if (section[i] == 13 && i + 1 < section.length && section[i + 1] == 10) {
                if (i + 2 < section.length && section[i + 2] == 32) { i += 3; continue; }
                break;
            }
            name.write(section[i++]);
        }
        return name.toString(StandardCharsets.UTF_8);
    }

    static void metadata(Path payload, Path layout, Path out, String createdBy, Instant signingTime) throws Exception {
        Manifest manifest = new Manifest();
        manifest.getMainAttributes().putValue("Manifest-Version", "1.0");
        manifest.getMainAttributes().putValue("Created-By", createdBy);
        MessageDigest md = MessageDigest.getInstance("SHA-256");
        byte[] buffer = new byte[65536];
        try (ZipFile zip = new ZipFile(payload.toFile())) {
            for (String[] row : layout(layout)) {
                ZipEntry entry = zip.getEntry(row[0]);
                if (entry == null) throw new IllegalArgumentException("missing payload entry");
                try (InputStream in = zip.getInputStream(entry)) {
                    for (int size; (size = in.read(buffer)) != -1;) md.update(buffer, 0, size);
                }
                Attributes attributes = new Attributes();
                attributes.putValue("SHA-256-Digest", Base64.getEncoder().encodeToString(md.digest()));
                manifest.getEntries().put(row[0], attributes);
            }
        }
        byte[] manifestBytes = serialize(manifest);
        int mainEnd = sectionEnd(manifestBytes, 0);
        Map<String, byte[]> sections = new HashMap<>();
        for (int start = mainEnd; start < manifestBytes.length;) {
            int end = sectionEnd(manifestBytes, start);
            byte[] section = Arrays.copyOfRange(manifestBytes, start, end);
            sections.put(sectionName(section), section);
            start = end;
        }
        Manifest signatureFile = new Manifest();
        Attributes main = signatureFile.getMainAttributes();
        main.putValue("Signature-Version", "1.0");
        main.putValue("Created-By", createdBy);
        main.putValue("SHA-256-Digest-Manifest", b64Digest(manifestBytes));
        main.putValue("SHA-256-Digest-Manifest-Main-Attributes", b64Digest(Arrays.copyOfRange(manifestBytes, 0, mainEnd)));
        for (String name : manifest.getEntries().keySet()) {
            Attributes attributes = new Attributes();
            attributes.putValue("SHA-256-Digest", b64Digest(sections.get(name)));
            signatureFile.getEntries().put(name, attributes);
        }
        byte[] signatureBytes = serialize(signatureFile);
        Files.createDirectories(out);
        Files.write(out.resolve("MANIFEST.MF"), manifestBytes);
        Files.write(out.resolve("SIGNATURE.SF"), signatureBytes);
        Files.write(out.resolve("signed-attributes.der"), signedAttributes(signatureBytes, signingTime));
        System.out.println("manifest_sha256=" + hexDigest(manifestBytes));
        System.out.println("signature_file_sha256=" + hexDigest(signatureBytes));
    }

    static String requiredEnvironment(String name) {
        String value = System.getenv(name);
        if (value == null || value.isEmpty()) throw new IllegalArgumentException("missing private signing environment: " + name);
        return value;
    }

    static String signatureName(String alias) {
        String override = System.getenv("BIRZZLE_SIGNATURE_NAME");
        String name = (override == null ? alias : override).toUpperCase(Locale.ENGLISH);
        if (name.length() > 8) name = name.substring(0, 8);
        return name.replaceAll("[^A-Z0-9_-]", "_");
    }

    static void sign(Path directory, String expectedCertificate, String expectedAttributes) throws Exception {
        byte[] attributes = Files.readAllBytes(directory.resolve("signed-attributes.der"));
        if (!hexDigest(attributes).equals(expectedAttributes)) throw new IllegalArgumentException("signed attributes hash mismatch");
        char[] storePassword = requiredEnvironment("BIRZZLE_STORE_PASSWORD").toCharArray();
        String keyPasswordText = System.getenv("BIRZZLE_KEY_PASSWORD");
        char[] keyPassword = keyPasswordText == null ? storePassword.clone() : keyPasswordText.toCharArray();
        try {
            KeyStore store = KeyStore.getInstance(Path.of(requiredEnvironment("BIRZZLE_KEYSTORE")).toFile(), storePassword);
            String alias = requiredEnvironment("BIRZZLE_KEY_ALIAS");
            X509Certificate certificate = (X509Certificate) store.getCertificate(alias);
            if (certificate == null || !hexDigest(certificate.getEncoded()).equals(expectedCertificate)) {
                throw new IllegalArgumentException("signer certificate mismatch");
            }
            PrivateKey key = (PrivateKey) store.getKey(alias, keyPassword);
            Signature signer = Signature.getInstance("SHA256withRSA");
            signer.initSign(key);
            signer.update(attributes);
            byte[] signature = signer.sign();
            signer.initVerify(certificate);
            signer.update(attributes);
            if (!signer.verify(signature)) throw new IllegalStateException("generated signature did not verify");
            byte[] implicitAttributes = attributes.clone();
            implicitAttributes[0] = (byte) 0xa0;
            byte[] one = der(2, new byte[] {1});
            byte[] signerInfo = seq(one,
                seq(certificate.getIssuerX500Principal().getEncoded(), der(2, certificate.getSerialNumber().toByteArray())),
                sha256Algorithm(), implicitAttributes, rsaSha256Algorithm(), der(4, signature));
            byte[] signedData = seq(one, sortedSet(sha256Algorithm()), seq(oid("2a864886f70d010701")),
                der(0xa0, certificate.getEncoded()), sortedSet(signerInfo));
            byte[] cms = seq(oid("2a864886f70d010702"), der(0xa0, signedData));
            Files.write(directory.resolve("SIGNATURE.RSA"), cms);
            Files.write(directory.resolve("signer-certificate.der"), certificate.getEncoded());
            System.out.println("signature_block_sha256=" + hexDigest(cms));
            System.out.println("certificate_sha256=" + hexDigest(certificate.getEncoded()));
        } finally {
            Arrays.fill(storePassword, '\0');
            Arrays.fill(keyPassword, '\0');
        }
    }

    static void add(ZipOutputStream output, String name, LocalDateTime time, int method,
                    long size, long crc, InputStream input) throws Exception {
        ZipEntry entry = new ZipEntry(name);
        entry.setTimeLocal(time);
        entry.setMethod(method);
        if (method == ZipEntry.STORED) { entry.setSize(size); entry.setCrc(crc); }
        output.putNextEntry(entry);
        input.transferTo(output);
        output.closeEntry();
    }

    static void pack(Path payload, Path layout, Path signing, Path output, LocalDateTime signatureTime) throws Exception {
        if (Files.exists(output)) throw new IllegalArgumentException("output APK already exists");
        String stem = signatureName(requiredEnvironment("BIRZZLE_KEY_ALIAS"));
        if (!stem.matches("[A-Z0-9_-]{1,8}")) throw new IllegalArgumentException("invalid signature entry name");
        try (ZipFile zip = new ZipFile(payload.toFile()); ZipOutputStream out = new ZipOutputStream(Files.newOutputStream(output))) {
            String[][] signatures = {{"MANIFEST.MF", "MANIFEST.MF"}, {"SIGNATURE.SF", stem + ".SF"}, {"SIGNATURE.RSA", stem + ".RSA"}};
            for (String[] item : signatures) {
                try (InputStream in = Files.newInputStream(signing.resolve(item[0]))) {
                    add(out, "META-INF/" + item[1], signatureTime, ZipEntry.DEFLATED, 0, 0, in);
                }
            }
            for (String[] row : layout(layout)) {
                ZipEntry entry = zip.getEntry(row[0]);
                if (entry == null) throw new IllegalArgumentException("missing payload entry");
                try (InputStream in = zip.getInputStream(entry)) {
                    add(out, row[0], LocalDateTime.parse(row[2]), Integer.parseInt(row[1]), entry.getSize(), entry.getCrc(), in);
                }
            }
        }
        System.out.println("APK written");
    }

    public static void main(String[] args) throws Exception {
        switch (args[0]) {
            case "metadata" -> metadata(Path.of(args[1]), Path.of(args[2]), Path.of(args[3]), args[4], Instant.parse(args[5]));
            case "sign" -> {
                try { sign(Path.of(args[1]), args[2], args[3]); }
                catch (Exception failure) {
                    // Provider errors may contain the private keystore path or alias.
                    System.err.println("Private signing failed (" + failure.getClass().getSimpleName() + "). Check local credentials and pinned public identity.");
                    System.exit(1);
                }
            }
            case "pack" -> pack(Path.of(args[1]), Path.of(args[2]), Path.of(args[3]), Path.of(args[4]), LocalDateTime.parse(args[5]));
            default -> throw new IllegalArgumentException("expected metadata, sign, or pack");
        }
    }
}
