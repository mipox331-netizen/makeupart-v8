import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:makeup_art_v8/services/favorite_image_store.dart';

void main() {
  late Directory root;

  setUp(() async {
    root = await Directory.systemTemp.createTemp('makeupart-favorites-');
  });

  tearDown(() async {
    if (await root.exists()) await root.delete(recursive: true);
  });

  test('favorites are persisted by job id and can be removed', () async {
    final store = FavoriteImageStore(rootOverride: root, scope: 'salon-1');
    final bytes = Uint8List.fromList([137, 80, 78, 71, 13, 10, 26, 10]);

    final saved = await store.save(bytes, jobId: 'job-123');
    expect(await store.contains('job-123'), isTrue);
    expect(await saved.readAsBytes(), orderedEquals(bytes));
    expect((await store.list()).length, 1);

    await store.remove('job-123');
    expect(await store.contains('job-123'), isFalse);
    expect(await store.list(), isEmpty);
  });

  test('favorites are isolated by salon scope', () async {
    final first = FavoriteImageStore(rootOverride: root, scope: 'salon-1');
    final second = FavoriteImageStore(rootOverride: root, scope: 'salon-2');
    final bytes = Uint8List.fromList([1, 2, 3]);

    await first.save(bytes, jobId: 'shared-job-id');

    expect(await first.contains('shared-job-id'), isTrue);
    expect(await second.contains('shared-job-id'), isFalse);
    expect(await second.list(), isEmpty);
  });

  test('empty bytes and unsafe empty ids are rejected', () async {
    final store = FavoriteImageStore(rootOverride: root, scope: 'salon-1');

    await expectLater(
      store.save(Uint8List(0), jobId: 'valid-id'),
      throwsArgumentError,
    );
    await expectLater(
      store.contains('../'),
      throwsArgumentError,
    );
  });
}
