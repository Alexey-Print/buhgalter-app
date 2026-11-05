package com.aleksey.uchet;

/** Keep the old /files/app directory intact during the first safe update. */
public class UchetActivity extends org.kivy.android.PythonActivity {
    @Override
    public String getAppRoot() {
        return getFilesDir().getAbsolutePath() + "/uchet_runtime";
    }
}
