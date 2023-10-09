package com.antmicro.update.rdfm;

import android.os.Bundle;

import androidx.fragment.app.FragmentActivity;
import androidx.preference.PreferenceFragmentCompat;

public class PreferenceActivity extends FragmentActivity {

    private static final String TAG = "PreferenceActivity";
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getSupportFragmentManager().beginTransaction()
                .replace(android.R.id.content, new PrefsFragment()).commit();
    }

    public static class PrefsFragment extends PreferenceFragmentCompat {

        public void onCreatePreferences(Bundle savedInstanceState, String rootKey) {
            super.onCreate(savedInstanceState);
            setPreferencesFromResource(R.xml.shared_preference, rootKey);
        }
    }
}
