import 'dart:typed_data';
import 'dart:ui' as ui;

/// Photo finishes are honest, local color grades applied to the processed
/// image; they do not claim to synthesize lipstick, eyeshadow, or hairstyles.
class PhotoLookService {
  static const names = <String>[
    'Natural Finish',
    'Warm Glow',
    'Soft Glam',
    'Studio Polish',
    'Golden Hour',
  ];

  static List<double> _matrixFor(String look) {
    switch (look) {
      case 'Warm Glow':
        return <double>[
          1.04, 0, 0, 0, 4,
          0, 1.01, 0, 0, 1,
          0, 0, 0.96, 0, -3,
          0, 0, 0, 1, 0,
        ];
      case 'Soft Glam':
        return <double>[
          1.05, 0.01, 0, 0, 4,
          0, 1.035, 0.005, 0, 3,
          0, 0.005, 1.02, 0, 2,
          0, 0, 0, 1, 0,
        ];
      case 'Studio Polish':
        return <double>[
          0.94, 0.04, 0.02, 0, 5,
          0.03, 0.94, 0.03, 0, 5,
          0.02, 0.04, 0.94, 0, 5,
          0, 0, 0, 1, 0,
        ];
      case 'Golden Hour':
        return <double>[
          1.08, 0.01, 0, 0, 5,
          0.01, 1.025, 0, 0, 2,
          0, 0.005, 0.90, 0, -5,
          0, 0, 0, 1, 0,
        ];
      case 'Natural Finish':
      default:
        return <double>[
          1, 0, 0, 0, 0,
          0, 1, 0, 0, 0,
          0, 0, 1, 0, 0,
          0, 0, 0, 1, 0,
        ];
    }
  }

  static Future<Uint8List> apply(Uint8List source, String look) async {
    if (source.isEmpty) {
      throw ArgumentError.value(source, 'source', 'Image bytes cannot be empty.');
    }
    if (!names.contains(look)) {
      throw ArgumentError.value(look, 'look', 'Unknown photo finish.');
    }
    if (look == 'Natural Finish') return Uint8List.fromList(source);

    final codec = await ui.instantiateImageCodec(source);
    try {
      final frame = await codec.getNextFrame();
      final input = frame.image;
      try {
        final recorder = ui.PictureRecorder();
        final canvas = ui.Canvas(recorder);
        canvas.drawImage(
          input,
          ui.Offset.zero,
          ui.Paint()
            ..filterQuality = ui.FilterQuality.high
            ..colorFilter = ui.ColorFilter.matrix(_matrixFor(look)),
        );
        final picture = recorder.endRecording();
        final output = await picture.toImage(input.width, input.height);
        try {
          final data = await output.toByteData(format: ui.ImageByteFormat.png);
          if (data == null) {
            throw StateError('Could not encode the finished image.');
          }
          return data.buffer.asUint8List(
            data.offsetInBytes,
            data.lengthInBytes,
          );
        } finally {
          output.dispose();
          picture.dispose();
        }
      } finally {
        input.dispose();
      }
    } finally {
      codec.dispose();
    }
  }
}
