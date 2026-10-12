import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:makeup_art_v8/services/photo_look_service.dart';

Future<Uint8List> _solidPng(Color color) async {
  final recorder = ui.PictureRecorder();
  final canvas = ui.Canvas(recorder);
  canvas.drawRect(
    const ui.Rect.fromLTWH(0, 0, 8, 8),
    ui.Paint()..color = color,
  );
  final picture = recorder.endRecording();
  final image = await picture.toImage(8, 8);
  try {
    final data = await image.toByteData(format: ui.ImageByteFormat.png);
    if (data == null) throw StateError('PNG encoding failed');
    return Uint8List.fromList(
      data.buffer.asUint8List(data.offsetInBytes, data.lengthInBytes),
    );
  } finally {
    image.dispose();
    picture.dispose();
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('natural finish preserves the original image bytes', () async {
    final source = await _solidPng(const Color(0xFF8090A0));
    final result = await PhotoLookService.apply(source, 'Natural Finish');
    expect(result, orderedEquals(source));
  });

  test('photo finish returns a valid PNG with the original dimensions', () async {
    final source = await _solidPng(const Color(0xFF8090A0));
    final result = await PhotoLookService.apply(source, 'Warm Glow');
    final codec = await ui.instantiateImageCodec(result);
    try {
      final frame = await codec.getNextFrame();
      expect(frame.image.width, 8);
      expect(frame.image.height, 8);
      frame.image.dispose();
    } finally {
      codec.dispose();
    }
  });

  test('unknown finish is rejected instead of silently ignored', () async {
    final source = await _solidPng(const Color(0xFF8090A0));
    await expectLater(
      PhotoLookService.apply(source, 'AI hairstyle'),
      throwsArgumentError,
    );
  });
}
