import 'package:flutter/services.dart';

class GalleryExporter {
  static const MethodChannel _channel = MethodChannel('makeupart/gallery');

  static Future<String> savePng({
    required List<int> bytes,
    required String fileName,
  }) async {
    if (bytes.isEmpty) {
      throw ArgumentError.value(bytes, 'bytes', 'Image bytes cannot be empty.');
    }
    final safeName = fileName.replaceAll(RegExp(r'[^A-Za-z0-9_.-]'), '_');
    final result = await _channel.invokeMethod<String>(
      'saveImage',
      {'bytes': bytes, 'fileName': safeName},
    );
    if (result == null || result.isEmpty) {
      throw StateError('The device did not confirm that the image was saved.');
    }
    return result;
  }
}
