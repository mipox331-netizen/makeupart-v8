package com.makeupart.makeup_art_v8

import android.Manifest
import android.content.ContentUris
import android.content.ContentValues
import android.content.pm.PackageManager
import android.database.Cursor
import java.io.File
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
            val safeName = requestedName.replace(Regex("[^A-Za-z0-9_.~-]"), "_")
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
        var newlyCreated = false
        try {
            // Reuse the deterministic app-owned MediaStore item on repeated
            // backup runs instead of creating a duplicate copy each time.
            uri = findExistingGalleryImage(fileName)
            if (uri != null) {
                val output = contentResolver.openOutputStream(uri, "wt")
                    ?: throw IllegalStateException("Unable to open existing gallery image")
                output.use { it.write(bytes) }
                result.success(uri.toString())
                return
            }

            val values = ContentValues().apply {
                put(MediaStore.Images.Media.DISPLAY_NAME, fileName)
                put(MediaStore.Images.Media.MIME_TYPE, "image/png")
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    put(
                        MediaStore.Images.Media.RELATIVE_PATH,
                        "${Environment.DIRECTORY_PICTURES}/MakeupArtV8/"
                    )
                    put(MediaStore.Images.Media.IS_PENDING, 1)
                } else {
                    val directory = galleryDirectory()
                    if (!directory.exists() && !directory.mkdirs()) {
                        throw IllegalStateException("Unable to create the MakeupArtV8 gallery folder")
                    }
                    put(
                        MediaStore.Images.Media.DATA,
                        File(directory, fileName).absolutePath
                    )
                }
            }

            uri = contentResolver.insert(
                MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
                values
            ) ?: throw IllegalStateException("Unable to create gallery image entry")
            newlyCreated = true

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
            // Remove only a newly-created incomplete row. An existing, valid
            // gallery backup must never be deleted because an overwrite failed.
            if (newlyCreated) {
                try {
                    uri?.let { contentResolver.delete(it, null, null) }
                } catch (cleanupException: Exception) {
                    Log.w("MakeupArtGallery", "Could not remove an incomplete gallery image", cleanupException)
                }
            }
            result.error(
                "GALLERY_SAVE_FAILED",
                exception.message ?: "Could not save image to the gallery.",
                null
            )
        }
    }

    private fun galleryDirectory(): File {
        return File(
            Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES),
            "MakeupArtV8"
        )
    }

    private fun findExistingGalleryImage(fileName: String): android.net.Uri? {
        val collection = MediaStore.Images.Media.EXTERNAL_CONTENT_URI
        val projection = arrayOf(MediaStore.Images.Media._ID)
        val selection: String
        val selectionArgs: Array<String>

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            selection = "${MediaStore.Images.Media.DISPLAY_NAME}=? AND ${MediaStore.Images.Media.RELATIVE_PATH}=?"
            selectionArgs = arrayOf(
                fileName,
                "${Environment.DIRECTORY_PICTURES}/MakeupArtV8/"
            )
        } else {
            selection = "${MediaStore.Images.Media.DATA}=?"
            selectionArgs = arrayOf(File(galleryDirectory(), fileName).absolutePath)
        }

        return contentResolver.query(
            collection,
            projection,
            selection,
            selectionArgs,
            null
        )?.use { cursor: Cursor ->
            if (cursor.moveToFirst()) {
                ContentUris.withAppendedId(
                    collection,
                    cursor.getLong(cursor.getColumnIndexOrThrow(MediaStore.Images.Media._ID))
                )
            } else {
                null
            }
        }
    }
}
}
