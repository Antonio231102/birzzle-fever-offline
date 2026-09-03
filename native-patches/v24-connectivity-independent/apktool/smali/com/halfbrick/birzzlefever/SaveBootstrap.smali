.class public final Lcom/halfbrick/birzzlefever/SaveBootstrap;
.super Ljava/lang/Object;
.source "SaveBootstrap.java"


# direct methods
.method public constructor <init>()V
    .locals 0

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

.method private static getExactTime(Ljava/util/zip/ZipEntry;)J
    .locals 8

    invoke-virtual {p0}, Ljava/util/zip/ZipEntry;->getExtra()[B

    move-result-object v0

    if-eqz v0, :fallback

    array-length v1, v0

    const/16 v2, 0x9

    if-lt v1, v2, :fallback

    const/4 v1, 0x0

    aget-byte v1, v0, v1

    and-int/lit16 v1, v1, 0xff

    const/16 v2, 0x55

    if-ne v1, v2, :fallback

    const/4 v1, 0x1

    aget-byte v1, v0, v1

    and-int/lit16 v1, v1, 0xff

    const/16 v2, 0x54

    if-ne v1, v2, :fallback

    const/4 v1, 0x2

    aget-byte v1, v0, v1

    and-int/lit16 v1, v1, 0xff

    const/4 v2, 0x5

    if-ne v1, v2, :fallback

    const/4 v1, 0x3

    aget-byte v1, v0, v1

    if-nez v1, :fallback

    const/4 v1, 0x4

    aget-byte v1, v0, v1

    and-int/lit8 v1, v1, 0x1

    if-eqz v1, :fallback

    const/4 v1, 0x5

    aget-byte v1, v0, v1

    and-int/lit16 v1, v1, 0xff

    int-to-long v3, v1

    const/4 v1, 0x6

    aget-byte v1, v0, v1

    and-int/lit16 v1, v1, 0xff

    int-to-long v5, v1

    const/16 v1, 0x8

    shl-long/2addr v5, v1

    or-long/2addr v3, v5

    const/4 v1, 0x7

    aget-byte v1, v0, v1

    and-int/lit16 v1, v1, 0xff

    int-to-long v5, v1

    const/16 v1, 0x10

    shl-long/2addr v5, v1

    or-long/2addr v3, v5

    const/16 v1, 0x8

    aget-byte v1, v0, v1

    and-int/lit16 v1, v1, 0xff

    int-to-long v5, v1

    const/16 v1, 0x18

    shl-long/2addr v5, v1

    or-long/2addr v3, v5

    const-wide/16 v5, 0x3e8

    mul-long/2addr v3, v5

    return-wide v3

    :fallback
    invoke-virtual {p0}, Ljava/util/zip/ZipEntry;->getTime()J

    move-result-wide v0

    return-wide v0
.end method

.method public static install(Landroid/content/Context;)V
    .locals 13

    :try_start_0
    invoke-virtual {p0}, Landroid/content/Context;->getApplicationInfo()Landroid/content/pm/ApplicationInfo;

    move-result-object v0

    iget-object v0, v0, Landroid/content/pm/ApplicationInfo;->dataDir:Ljava/lang/String;

    new-instance v1, Ljava/io/File;

    invoke-direct {v1, v0}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    new-instance v2, Ljava/io/File;

    const-string v3, ".birzzle_seed_v1"

    invoke-direct {v2, v1, v3}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

    invoke-virtual {v2}, Ljava/io/File;->exists()Z

    move-result v3

    if-nez v3, :cond_6

    new-instance v3, Ljava/io/File;

    const-string v4, "files/profile"

    invoke-direct {v3, v1, v4}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

    invoke-virtual {v3}, Ljava/io/File;->exists()Z

    move-result v3

    if-eqz v3, :cond_0

    invoke-virtual {v2}, Ljava/io/File;->createNewFile()Z

    goto/16 :goto_3

    :cond_0
    invoke-virtual {v1}, Ljava/io/File;->getCanonicalPath()Ljava/lang/String;

    move-result-object v3

    new-instance v4, Ljava/lang/StringBuilder;

    invoke-direct {v4}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {v4, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v4

    sget-object v5, Ljava/io/File;->separator:Ljava/lang/String;

    invoke-virtual {v4, v5}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v4

    invoke-virtual {v4}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v3

    invoke-virtual {p0}, Landroid/content/Context;->getAssets()Landroid/content/res/AssetManager;

    move-result-object v4

    const-string v5, "birzzle_seed_v1.zip"

    invoke-virtual {v4, v5}, Landroid/content/res/AssetManager;->open(Ljava/lang/String;)Ljava/io/InputStream;

    move-result-object v4

    new-instance v5, Ljava/util/zip/ZipInputStream;

    invoke-direct {v5, v4}, Ljava/util/zip/ZipInputStream;-><init>(Ljava/io/InputStream;)V

    const/16 v4, 0x2000

    new-array v4, v4, [B

    :goto_0
    invoke-virtual {v5}, Ljava/util/zip/ZipInputStream;->getNextEntry()Ljava/util/zip/ZipEntry;

    move-result-object v6

    if-eqz v6, :cond_5

    invoke-virtual {v6}, Ljava/util/zip/ZipEntry;->getName()Ljava/lang/String;

    move-result-object v7

    new-instance v8, Ljava/io/File;

    invoke-direct {v8, v1, v7}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

    invoke-virtual {v8}, Ljava/io/File;->getCanonicalPath()Ljava/lang/String;

    move-result-object v7

    invoke-virtual {v7, v3}, Ljava/lang/String;->startsWith(Ljava/lang/String;)Z

    move-result v7

    if-eqz v7, :cond_4

    invoke-virtual {v6}, Ljava/util/zip/ZipEntry;->isDirectory()Z

    move-result v7

    if-eqz v7, :cond_1

    invoke-virtual {v8}, Ljava/io/File;->mkdirs()Z

    goto :goto_2

    :cond_1
    invoke-virtual {v8}, Ljava/io/File;->getParentFile()Ljava/io/File;

    move-result-object v7

    invoke-virtual {v7}, Ljava/io/File;->mkdirs()Z

    new-instance v7, Ljava/io/FileOutputStream;

    invoke-direct {v7, v8}, Ljava/io/FileOutputStream;-><init>(Ljava/io/File;)V

    :goto_1
    invoke-virtual {v5, v4}, Ljava/util/zip/ZipInputStream;->read([B)I

    move-result v9

    const/4 v10, -0x1

    if-eq v9, v10, :cond_2

    const/4 v10, 0x0

    invoke-virtual {v7, v4, v10, v9}, Ljava/io/FileOutputStream;->write([BII)V

    goto :goto_1

    :cond_2
    invoke-virtual {v7}, Ljava/io/FileOutputStream;->close()V

    invoke-static {v6}, Lcom/halfbrick/birzzlefever/SaveBootstrap;->getExactTime(Ljava/util/zip/ZipEntry;)J

    move-result-wide v9

    const-wide/16 v11, 0x0

    cmp-long v7, v9, v11

    if-lez v7, :cond_3

    invoke-virtual {v8, v9, v10}, Ljava/io/File;->setLastModified(J)Z

    :cond_3
    :goto_2
    invoke-virtual {v5}, Ljava/util/zip/ZipInputStream;->closeEntry()V

    goto :goto_0

    :cond_4
    new-instance v0, Ljava/io/IOException;

    const-string v1, "Unsafe seed path"

    invoke-direct {v0, v1}, Ljava/io/IOException;-><init>(Ljava/lang/String;)V

    throw v0

    :cond_5
    invoke-virtual {v5}, Ljava/util/zip/ZipInputStream;->close()V

    invoke-virtual {v2}, Ljava/io/File;->createNewFile()Z

    const-string v0, "[BirzzleSeed]"

    const-string v1, "Installed embedded 2016 save"

    invoke-static {v0, v1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0

    goto :goto_3

    :catch_0
    move-exception v0

    const-string v1, "[BirzzleSeed]"

    const-string v2, "Unable to install embedded save"

    invoke-static {v1, v2, v0}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    :cond_6
    :goto_3
    return-void
.end method
