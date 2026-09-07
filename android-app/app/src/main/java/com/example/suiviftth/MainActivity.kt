package com.example.suiviftth

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.DocumentsContract
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat

class MainActivity : ComponentActivity() {
    private lateinit var webView: WebView
    private var filePathCallback: ValueCallback<Array<Uri>>? = null

    companion object {
        private const val PREFS_NAME = "suivi_ftth_prefs"
        private const val KEY_LAST_FOLDER_URI = "last_folder_uri"
    }

    // Gestionnaire pour le retour du sélecteur de fichiers
    private val filePickerLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        // Utilisation de parseResult qui gère nativement data et clipData !
        val results = WebChromeClient.FileChooserParams.parseResult(result.resultCode, result.data)
        filePathCallback?.onReceiveValue(results)
        filePathCallback = null

        // Mémoriser automatiquement l'emplacement du fichier sélectionné
        if (result.resultCode == Activity.RESULT_OK && !results.isNullOrEmpty()) {
            saveLastLocation(results[0], result.data)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // 1. Création de la mise en page principale
        val layout = FrameLayout(this)
        
        // 2. Création du WebView
        webView = WebView(this)
        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.settings.allowFileAccess = true
        webView.settings.allowContentAccess = true
        webView.webViewClient = WebViewClient()
        
        // Gérer l'upload de fichiers
        webView.webChromeClient = object : WebChromeClient() {
            override fun onShowFileChooser(
                webView: WebView?,
                filePathCallback: ValueCallback<Array<Uri>>?,
                fileChooserParams: FileChooserParams?
            ): Boolean {
                this@MainActivity.filePathCallback?.onReceiveValue(null)
                this@MainActivity.filePathCallback = filePathCallback

                try {
                    val intent = fileChooserParams?.createIntent() ?: Intent(Intent.ACTION_GET_CONTENT).apply {
                        addCategory(Intent.CATEGORY_OPENABLE)
                        type = "*/*"
                    }

                    // Ouvrir directement dans le dernier dossier utilisé si disponible
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        val prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
                        val lastUriStr = prefs.getString(KEY_LAST_FOLDER_URI, null)
                        if (!lastUriStr.isNullOrEmpty()) {
                            try {
                                val initialUri = Uri.parse(lastUriStr)
                                intent.putExtra(DocumentsContract.EXTRA_INITIAL_URI, initialUri)
                                intent.putExtra("android.provider.extra.INITIAL_URI", initialUri)
                            } catch (_: Exception) {}
                        }
                    }

                    filePickerLauncher.launch(intent)
                } catch (e: Exception) {
                    this@MainActivity.filePathCallback = null
                    return false
                }
                return true
            }
        }
        
        layout.addView(webView)
        setContentView(layout)
        
        // 3. Gérer le débordement sur la barre de statut (Edge-to-Edge Android 15+)
        ViewCompat.setOnApplyWindowInsetsListener(layout) { view, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            view.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }
        
        webView.loadUrl("https://tech.sse.sn")
    }

    private fun saveLastLocation(selectedUri: Uri, data: Intent?) {
        try {
            // Tenter d'obtenir la permission persistante si offerte
            try {
                val takeFlags: Int = (data?.flags ?: 0) and (
                    Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                )
                if (takeFlags != 0) {
                    contentResolver.takePersistableUriPermission(selectedUri, takeFlags)
                }
            } catch (_: Exception) {}

            var targetUri = selectedUri

            // Sur Android 8.0+, si c'est un DocumentUri, tenter de cibler le dossier parent
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O && DocumentsContract.isDocumentUri(this, selectedUri)) {
                val docId = DocumentsContract.getDocumentId(selectedUri)
                val authority = selectedUri.authority
                if (authority != null && docId != null && docId.contains("/")) {
                    val parentDocId = docId.substringBeforeLast('/')
                    try {
                        targetUri = DocumentsContract.buildDocumentUri(authority, parentDocId)
                    } catch (_: Exception) {
                        targetUri = selectedUri
                    }
                }
            }

            getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
                .edit()
                .putString(KEY_LAST_FOLDER_URI, targetUri.toString())
                .apply()
        } catch (e: Exception) {
            try {
                getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
                    .edit()
                    .putString(KEY_LAST_FOLDER_URI, selectedUri.toString())
                    .apply()
            } catch (_: Exception) {}
        }
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }
}
