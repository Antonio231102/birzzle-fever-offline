package de.robv.android.xposed;

import java.util.Set;

public final class XposedBridge {
    public static Set<XC_MethodHook> hookAllMethods(
            Class<?> hookClass, String methodName, XC_MethodHook callback) {
        return null;
    }

    public static void log(String text) {
    }
}
