import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:makeup_art_v8/services/recent_image_store.dart';

Future<int> countPngFiles(Directory directory) async {
  if (!await directory.exists()) return 0;
  final files = await directory
      .list()
      .where((entity) => entity is File)
      .cast<File>()
      .where((file) => file.path.toLowerCase().endsWith('.png'))
      .toList();
  return files.length;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('keeps only ten recent results in app storage and archives overflow', () async {
    final root = await Directory.systemTemp.createTemp('makeupart_recent_');
    final phoneRoot = await Directory.systemTemp.createTemp('makeupart_phone_');
    const scope = 'test-salon';
    final store = RecentImageStore(
      rootOverride: root,
      phoneRootOverride: phoneRoot,
      scope: scope,
    );

    try {
      for (var index = 0; index < 12; index++) {
        await store.save(
          Uint8List.fromList(List<int>.filled(16, index)),
          jobId: 'job-$index',
        );
        await Future<void>.delayed(const Duration(milliseconds: 2));
      }

      final privateDirectory = Directory(
        '${root.path}${Platform.pathSeparator}recent_ai_results'
        '${Platform.pathSeparator}$scope',
      );
      final phoneDirectory = Directory(
        '${phoneRoot.path}${Platform.pathSeparator}MakeupArtV8'
        '${Platform.pathSeparator}$scope',
      );

      expect(await store.list(), hasLength(10));
      expect(await countPngFiles(privateDirectory), 10);
      expect(await countPngFiles(phoneDirectory), 2);
    } finally {
      await root.delete(recursive: true);
      await phoneRoot.delete(recursive: true);
    }
  });

  test('preserves overflow when external phone storage is unavailable', () async {
    final root = await Directory.systemTemp.createTemp('makeupart_recent_fallback_');
    final store = RecentImageStore(rootOverride: root);

    try {
      for (var index = 0; index < 11; index++) {
        await store.save(
          Uint8List.fromList(List<int>.filled(16, index)),
          jobId: 'job-$index',
        );
        await Future<void>.delayed(const Duration(milliseconds: 2));
      }

      final privateDirectory = Directory(
        '${root.path}${Platform.pathSeparator}recent_ai_results'
        '${Platform.pathSeparator}default',
      );
      expect(await store.list(), hasLength(10));
      expect(await countPngFiles(privateDirectory), 11);
    } finally {
      await root.delete(recursive: true);
    }
  });
}
