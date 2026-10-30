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
    final galleryRoot = await Directory.systemTemp.createTemp('makeupart_gallery_');
    const scope = 'test-salon';
    final store = RecentImageStore(
      rootOverride: root,
      scope: scope,
      galleryArchiveWriter: (bytes, fileName) async {
        final directory = Directory(
          '${galleryRoot.path}${Platform.pathSeparator}Pictures'
          '${Platform.pathSeparator}MakeupArtV8',
        );
        await directory.create(recursive: true);
        await File('${directory.path}${Platform.pathSeparator}$fileName')
            .writeAsBytes(bytes, flush: true);
      },
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
      final galleryDirectory = Directory(
        '${galleryRoot.path}${Platform.pathSeparator}Pictures'
        '${Platform.pathSeparator}MakeupArtV8',
      );

      expect(await store.list(), hasLength(10));
      expect(await countPngFiles(privateDirectory), 10);
      expect(await countPngFiles(galleryDirectory), 2);
      final archivedNames = await galleryDirectory
          .list()
          .where((entity) => entity is File)
          .cast<File>()
          .map((file) => file.uri.pathSegments.last)
          .toList();
      expect(
        archivedNames.every((name) => name.startsWith('archive_${scope}_')),
        isTrue,
      );
    } finally {
      await root.delete(recursive: true);
      await galleryRoot.delete(recursive: true);
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

  test('different salon IDs never share private history or archived gallery images', () async {
    final root = await Directory.systemTemp.createTemp('makeupart_recent_isolation_');
    final galleryRoot = await Directory.systemTemp.createTemp('makeupart_gallery_isolation_');
    final galleryDirectory = Directory(
      '${galleryRoot.path}${Platform.pathSeparator}Pictures'
      '${Platform.pathSeparator}MakeupArtV8',
    );
    Future<void> archive(Uint8List bytes, String fileName) async {
      await galleryDirectory.create(recursive: true);
      await File(
        '${galleryDirectory.path}${Platform.pathSeparator}$fileName',
      ).writeAsBytes(bytes, flush: true);
    }

    final first = RecentImageStore(
      rootOverride: root,
      galleryArchiveWriter: archive,
      scope: 'salon:one',
    );
    // This literal safe salon ID is the Base64URL token for "salon:one".
    // It must remain distinct from the encoded unsafe ID in Gallery filenames.
    final second = RecentImageStore(
      rootOverride: root,
      galleryArchiveWriter: archive,
      scope: 'c2Fsb246b25l',
    );

    try {
      for (var index = 0; index < 11; index++) {
        await first.save(
          Uint8List.fromList(List<int>.filled(16, index)),
          jobId: 'first-$index',
        );
        await Future<void>.delayed(const Duration(milliseconds: 2));
      }
      for (var index = 0; index < 11; index++) {
        await second.save(
          Uint8List.fromList(List<int>.filled(16, 100 + index)),
          jobId: 'second-$index',
        );
        await Future<void>.delayed(const Duration(milliseconds: 2));
      }

      expect(await first.list(), hasLength(10));
      expect(await second.list(), hasLength(10));
      final firstScope = '~${base64Url.encode(utf8.encode('salon:one')).replaceAll('=', '')}';
      const secondScope = 'c2Fsb246b25l';
      final archivedFiles = await galleryDirectory
          .list()
          .where((entity) => entity is File)
          .cast<File>()
          .toList();
      final firstArchives = archivedFiles
          .where((file) => file.uri.pathSegments.last.startsWith('archive_${firstScope}_'))
          .toList();
      final secondArchives = archivedFiles
          .where((file) => file.uri.pathSegments.last.startsWith('archive_${secondScope}_'))
          .toList();
      expect(firstArchives, hasLength(1));
      expect(secondArchives, hasLength(1));
      expect(
        await firstArchives.single.readAsBytes(),
        equals(List<int>.filled(16, 0)),
      );
      expect(
        await secondArchives.single.readAsBytes(),
        equals(List<int>.filled(16, 100)),
      );
    } finally {
      await root.delete(recursive: true);
      await galleryRoot.delete(recursive: true);
    }
  });

  test('different job IDs cannot collapse to the same history filename', () async {
    final root = await Directory.systemTemp.createTemp('makeupart_recent_job_ids_');
    final store = RecentImageStore(rootOverride: root, scope: 'test-salon');

    try {
      await store.save(Uint8List.fromList([1, 2, 3]), jobId: 'work:one');
      await store.save(Uint8List.fromList([7, 8, 9]), jobId: 'work?one');

      final files = await store.list();
      expect(files, hasLength(2));
      final contents = <String>{
        for (final file in files) (await file.readAsBytes()).join(','),
      };
      expect(contents, contains('1,2,3'));
      expect(contents, contains('7,8,9'));
    } finally {
      await root.delete(recursive: true);
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

  test('keeps the only private copy when public gallery archiving fails', () async {
    final root = await Directory.systemTemp.createTemp('makeupart_recent_gallery_failure_');
    final store = RecentImageStore(
      rootOverride: root,
      scope: 'salon-failure',
      galleryArchiveWriter: (bytes, fileName) async {
        throw StateError('simulated MediaStore failure');
      },
    );

    try {
      for (var index = 0; index < 11; index++) {
        await store.save(
          Uint8List.fromList(List<int>.filled(16, index)),
          jobId: 'job-$index',
        );
      }

      final privateDirectory = Directory(
        '${root.path}${Platform.pathSeparator}recent_ai_results'
        '${Platform.pathSeparator}salon-failure',
      );
      expect(await store.list(), hasLength(10));
      // The overflow is no longer in the visible ten-item recent list,
      // but the only source copy is retained when gallery publication fails.
      expect(await countPngFiles(privateDirectory), 11);
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

      const defaultScope = 'default';
      final privateDirectory = Directory(
        '${root.path}${Platform.pathSeparator}recent_ai_results'
        '${Platform.pathSeparator}$defaultScope',
      );
      expect(await store.list(), hasLength(10));
      expect(await countPngFiles(privateDirectory), 11);
    } finally {
      await root.delete(recursive: true);
    }
  });
}
