import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:makeup_art_v8/services/recent_image_store.dart';

void main() {
  test('keeps only the ten newest AI results', () async {
    final root = await Directory.systemTemp.createTemp('makeupart_recent_');
    final store = RecentImageStore(rootOverride: root, scope: 'test-salon');

    try {
      for (var index = 0; index < 12; index++) {
        await store.save(
          Uint8List.fromList(List<int>.filled(16, index)),
          jobId: 'job-$index',
        );
        await Future<void>.delayed(const Duration(microseconds: 10));
      }

      final recent = await store.list();
      final allFiles = await Directory(
        '${root.path}${Platform.pathSeparator}recent_ai_results${Platform.pathSeparator}test-salon',
      )
          .list()
          .where((entity) => entity is File)
          .cast<File>()
          .toList();

      expect(recent.length, 10);
      expect(allFiles.length, 10);
      expect(
        recent.every((file) => file.existsSync()),
        isTrue,
      );
    } finally {
      await root.delete(recursive: true);
    }
  });
}