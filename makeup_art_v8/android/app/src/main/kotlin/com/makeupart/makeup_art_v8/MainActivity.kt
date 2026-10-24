package com.makeupart.makeup_art_v8

import android.Manifest
import android.content.ContentValues
import android.content.pm.PackageManager
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.util.Log
import androidx.core.content.ContextCompat
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private data class PendingGallerySave(
        val bytes: ByteArray,
        val fileName: String,
        val result: MethodChannel.Result
    )

    private var pendingGallerySave: PendingGallerySave? = null

    companion object {
        private const val GALLERY_CHANNEL = "makeupart/gallery"
        private const val WRITE_GALLERY_PERMISSION_REQUEST = 8427
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            GALLERY_CHANNEL
        ).setMethodCallHandler { call, result ->
            if (call.method != "saveImage") {
                result.notImplemented()
                return@setMethodCallHandler
            }

            val bytes = call.argument<ByteArray>("bytes")
            val requestedName = call.argument<String>("fileName") ?: "makeupart-result.png"
            val safeName = requestedName.replace(Regex("[^A-Za-z0-9_.-]"), "_")
            if (bytes == null || bytes.isEmpty()) {
                result.error("EMPTY_IMAGE", "Image data is empty.", null)
                return@setMethodCallHandler
            }

            if (
                Build.VERSION.SDK_INT < Build.VERSION_CODES.Q &&
                ContextCompat.checkSelfPermission(
                    this,
                    Manifest.permission.WRITE_EXTERNAL_STORAGE
                ) != PackageManager.PERMISSION_GRANTED
            ) {
                if (pendingGallerySave != null) {
                    result.error(
                        "SAVE_IN_PROGRESS",
                        "A gallery save is already waiting for permission.",
                        null
                    )
                    return@setMethodCallHandler
                }
                pendingGallerySave = PendingGallerySave(bytes, safeName, result)
                requestPermissions(
                    arrayOf(Manifest.permission.WRITE_EXTERNAL_STORAGE),
                    WRITE_GALLERY_PERMISSION_REQUEST
                )
                return@setMethodCallHandler
            }

            saveImageToGallery(bytes, safeName, result)
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode != WRITE_GALLERY_PERMISSION_REQUEST) return

        val pending = pendingGallerySave
        pendingGallerySave = null
        if (pending == null) return

        if (grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) {
            saveImageToGallery(pending.bytes, pending.fileName, pending.result)
        } else {
            pending.result.error(
                "GALLERY_PERMISSION_DENIED",
                "Allow storage access to save the image on this older Android version.",
                null
            )
        }
    }

    private fun saveImageToGallery(
        bytes: ByteArray,
        fileName: String,
        result: MethodChannel.Result
    ) {
        var uri: android.net.Uri? = null
        try {
            val values = ContentValues().apply {
                put(MediaStore.Images.Media.DISPLAY_NAME, fileName)
                put(MediaStore.Images.Media.MIME_TYPE, "image/png")
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    put(
                        MediaStore.Images.Media.RELATIVE_PATH,
                        "${Environment.DIRECTORY_PICTURES}/MakeupArtV8"
                    )
                    put(MediaStore.Images.Media.IS_PENDING, 1)
                }
            }
            uri = contentResolver.insert(
                MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
                values
            ) ?: throw IllegalStateException("Unable to create gallery image entry")

            val output = contentResolver.openOutputStream(uri)
                ?: throw IllegalStateException("Unable to open gallery image output")
            output.use { it.write(bytes) }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val published = ContentValues().apply {
                    put(MediaStore.Images.Media.IS_PENDING, 0)
                }
                val updatedRows = contentResolver.update(uri, published, null, null)
                if (updatedRows != 1) {
                    throw IllegalStateException("The device did not publish the saved image to Gallery")
                }
            }
            result.success(uri.toString())
        } catch (exception: Exception) {
            try {
                uri?.let { contentResolver.delete(it, null, null) }
            } catch (cleanupException: Exception) {
                Log.w("MakeupArtGallery", "Could not remove an incomplete gallery image", cleanupException)
            }
            result.error(
                "GALLERY_SAVE_FAILED",
                exception.message ?: "Could not save image to the gallery.",
                null
            )
        }
    }
}
