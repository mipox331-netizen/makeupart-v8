import 'dart:convert';
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
    final safeScope = base64Url.encode(utf8.encode(scope)).replaceAll('=', '');
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
        '${Platform.pathSeparator}$safeScope',
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

  test('updates the existing history item when a job is saved again', () async {
    final root = await Directory.systemTemp.createTemp('makeupart_recent_dedupe_');
    final store = RecentImageStore(rootOverride: root, scope: 'test-salon');

    try {
      final original = await store.save(
        Uint8List.fromList([1, 2, 3]),
        jobId: 'same-job',
      );
      final updated = await store.save(
        Uint8List.fromList([7, 8, 9]),
        jobId: 'same-job',
      );

      expect(updated.path, original.path);
      expect(await store.list(), hasLength(1));
      expect(await updated.readAsBytes(), equals([7, 8, 9]));
    } finally {
      await root.delete(recursive: true);
    }
  });

  test('different salon IDs never share private history or archived storage', () async {
    final root = await Directory.systemTemp.createTemp('makeupart_recent_isolation_');
    final phoneRoot = await Directory.systemTemp.createTemp('makeupart_phone_isolation_');
    final first = RecentImageStore(
      rootOverride: root,
      phoneRootOverride: phoneRoot,
      scope: 'salon:one',
    );
    final second = RecentImageStore(
      rootOverride: root,
      phoneRootOverride: phoneRoot,
      scope: 'salon?one',
    );

    try {
      await first.save(Uint8List.fromList([1, 2, 3]), jobId: 'same-job');
      await second.save(Uint8List.fromList([7, 8, 9]), jobId: 'same-job');

      expect(await first.list(), hasLength(1));
      expect(await second.list(), hasLength(1));
      expect(await (await first.list()).single.readAsBytes(), equals([1, 2, 3]));
      expect(await (await second.list()).single.readAsBytes(), equals([7, 8, 9]));

      final firstArchive = Directory(
        '${phoneRoot.path}${Platform.pathSeparator}MakeupArtV8'
        '${Platform.pathSeparator}${base64Url.encode(utf8.encode('salon:one')).replaceAll('=', '')}',
      );
      final secondArchive = Directory(
        '${phoneRoot.path}${Platform.pathSeparator}MakeupArtV8'
        '${Platform.pathSeparator}${base64Url.encode(utf8.encode('salon?one')).replaceAll('=', '')}',
      );
      expect(firstArchive.path, isNot(secondArchive.path));
    } finally {
      await root.delete(recursive: true);
      await phoneRoot.delete(recursive: true);
    }
  });

  test('rejects an empty salon scope', () async {
    final root = await Directory.systemTemp.createTemp('makeupart_recent_empty_scope_');
    final store = RecentImageStore(rootOverride: root, scope: '  ');
    try {
      await expectLater(store.list(), throwsArgumentError);
    } finally {
      await root.delete(recursive: true);
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
