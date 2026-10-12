package com.makeupart.makeup_art_v8

import android.content.ContentValues
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            "makeupart/gallery"
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

            try {
                val values = ContentValues().apply {
                    put(MediaStore.Images.Media.DISPLAY_NAME, safeName)
                    put(MediaStore.Images.Media.MIME_TYPE, "image/png")
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                        put(
                            MediaStore.Images.Media.RELATIVE_PATH,
                            "${Environment.DIRECTORY_PICTURES}/MakeupArtV8"
                        )
                        put(MediaStore.Images.Media.IS_PENDING, 1)
                    }
                }
                val uri = contentResolver.insert(
                    MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
                    values
                ) ?: throw IllegalStateException("Unable to create gallery image entry")

                try {
                    val output = contentResolver.openOutputStream(uri)
                        ?: throw IllegalStateException("Unable to open gallery image output")
                    output.use { it.write(bytes) }

                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                        val published = ContentValues().apply {
                            put(MediaStore.Images.Media.IS_PENDING, 0)
                        }
                        contentResolver.update(uri, published, null, null)
                    }
                    result.success(uri.toString())
                } catch (exception: Exception) {
                    contentResolver.delete(uri, null, null)
                    throw exception
                }
            } catch (exception: Exception) {
                result.error(
                    "GALLERY_SAVE_FAILED",
                    exception.message ?: "Could not save image to the gallery.",
                    null
                )
            }
        }
    }
}
