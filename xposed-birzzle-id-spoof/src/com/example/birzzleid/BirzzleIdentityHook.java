package com.example.birzzleid;

import de.robv.android.xposed.IXposedHookLoadPackage;
import de.robv.android.xposed.XC_MethodReplacement;
import de.robv.android.xposed.XposedBridge;
import de.robv.android.xposed.XposedHelpers;
import de.robv.android.xposed.callbacks.XC_LoadPackage;

public final class BirzzleIdentityHook implements IXposedHookLoadPackage {
    private static final String TARGET_PACKAGE = "com.halfbrick.birzzlefever";
    private static final String TARGET_CLASS = "com.halfbrick.birzzlefever.BirzzleFever";
    private static final String ORIGINAL_GAME_ID =
            "3c8bb7308c3fcb60c439224bd595c794d8f31501";

    @Override
    public void handleLoadPackage(XC_LoadPackage.LoadPackageParam loadPackageParam)
            throws Throwable {
        if (!TARGET_PACKAGE.equals(loadPackageParam.packageName)) {
            return;
        }

        Class<?> target = XposedHelpers.findClass(TARGET_CLASS, loadPackageParam.classLoader);
        int hooked = XposedBridge.hookAllMethods(
                target,
                "GetUniqueDeviceID",
                XC_MethodReplacement.returnConstant(ORIGINAL_GAME_ID)).size();

        int reachableHooks = XposedBridge.hookAllMethods(
                target,
                "Network_IsReachable",
                XC_MethodReplacement.returnConstant(false)).size();

        int stateHooks = XposedBridge.hookAllMethods(
                target,
                "Network_GetState",
                XC_MethodReplacement.returnConstant(0)).size();

        XposedBridge.log("BirzzleIdentitySpoof: hooked " + hooked
                + " GetUniqueDeviceID method(s); returning " + ORIGINAL_GAME_ID);
        XposedBridge.log("BirzzleIdentitySpoof: offline mode active; hooked "
                + reachableHooks + " Network_IsReachable method(s) and "
                + stateHooks + " Network_GetState method(s)");
    }
}
