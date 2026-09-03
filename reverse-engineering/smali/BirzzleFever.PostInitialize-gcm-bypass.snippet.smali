# Accepted V24 insertion after MakeContactJson(contact).
# :goto_0 is the existing post-registration continuation in the surrounding
# decompiled method. The original registration implementation remains below it
# but is unreachable through this inserted branch.

    const-string v5, ""

    invoke-static {v5}, Lcom/halfbrick/birzzlefever/BirzzleFever;->nativeSetGCMRegisterId(Ljava/lang/String;)V

    sput-object v5, Lcom/halfbrick/birzzlefever/BirzzleFever;->GCMID:Ljava/lang/String;

    goto :goto_0
