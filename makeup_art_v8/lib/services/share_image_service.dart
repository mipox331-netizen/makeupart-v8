import 'package:flutter/services.dart';

/// Opens the native Android/iOS share sheet with the finished PNG and caption.
class ShareImageService {
  static const MethodChannel _channel = MethodChannel('makeupart/gallery');

  static Future<void> sharePng({
    required Uint8List bytes,
    required String fileName,
    required String caption,
  }) async {
    if (bytes.isEmpty) {
      throw ArgumentError.value(bytes, 'bytes', 'Image bytes cannot be empty.');
    }
    final safeName = fileName.replaceAll(RegExp(r'[^A-Za-z0-9_.-]'), '_');
    final result = await _channel.invokeMethod<bool>(
      'shareImage',
      {
        'bytes': bytes,
        'fileName': safeName,
        'text': caption,
      },
    );
    if (result != true) {
      throw StateError('The device did not confirm that the share sheet opened.');
    }
  }
}
