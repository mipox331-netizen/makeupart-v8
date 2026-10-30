import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:makeup_art_v8/services/salon_look_preset_store.dart';

void main() {
  late Directory root;

  setUp(() async {
    root = await Directory.systemTemp.createTemp('makeupart-look-presets-');
  });

  tearDown(() async {
    if (await root.exists()) await root.delete(recursive: true);
  });

  test('persists the complete look recipe and isolates salons', () async {
    final salonA = SalonLookPresetStore(rootOverride: root, scope: 'salon-a');
    final salonB = SalonLookPresetStore(rootOverride: root, scope: 'salon-b');

    final saved = await salonA.save(
      name: 'Bridal Rose',
      folder: 'Makeup',
      engine: 'classic',
      makeupStyle: 'bridal_rose',
      generativeLook: 'bridal_glam',
      photoFinish: 'Golden Hour',
      intensity: 0.82,
    );

    final loaded = await salonA.list();
    expect(loaded, hasLength(1));
    expect(loaded.single.id, saved.id);
    expect(loaded.single.name, 'Bridal Rose');
    expect(loaded.single.folder, 'Makeup');
    expect(loaded.single.engine, 'classic');
    expect(loaded.single.makeupStyle, 'bridal_rose');
    expect(loaded.single.generativeLook, 'bridal_glam');
    expect(loaded.single.photoFinish, 'Golden Hour');
    expect(loaded.single.intensity, closeTo(0.82, 0.0001));
    expect(await salonB.list(), isEmpty);
  });

  test('salon scopes cannot collide after path normalization', () async {
    final first = SalonLookPresetStore(rootOverride: root, scope: 'salon:one');
    final second = SalonLookPresetStore(rootOverride: root, scope: 'salon?one');

    await first.save(
      name: 'Natural',
      folder: 'Skin',
      engine: 'classic',
      makeupStyle: 'skin_only',
      generativeLook: 'natural',
      photoFinish: 'Natural Finish',
      intensity: 0.5,
    );
    await second.save(
      name: 'Natural',
      folder: 'Skin',
      engine: 'classic',
      makeupStyle: 'skin_only',
      generativeLook: 'natural',
      photoFinish: 'Natural Finish',
      intensity: 0.5,
    );

    expect(await first.list(), hasLength(1));
    expect(await second.list(), hasLength(1));
    await expectLater(
      SalonLookPresetStore(rootOverride: root, scope: '  ').list(),
      throwsArgumentError,
    );
  });

  test('saving an existing name updates it instead of creating a duplicate', () async {
    final store = SalonLookPresetStore(rootOverride: root, scope: 'salon-a');

    final first = await store.save(
      name: 'Natural',
      folder: 'Skin',
      engine: 'classic',
      makeupStyle: 'skin_only',
      generativeLook: 'natural',
      photoFinish: 'Natural Finish',
      intensity: 0.4,
    );
    final updated = await store.save(
      name: '  natural  ',
      folder: 'Impression',
      engine: 'classic',
      makeupStyle: 'skin_only',
      generativeLook: 'natural',
      photoFinish: 'Warm Glow',
      intensity: 0.65,
    );

    final saved = await store.list();
    expect(saved, hasLength(1));
    expect(updated.id, first.id);
    expect(saved.single.name, 'natural');
    expect(saved.single.folder, 'Impression');
    expect(saved.single.photoFinish, 'Warm Glow');
    expect(saved.single.intensity, closeTo(0.65, 0.0001));
  });

  test('rejects empty names, unsupported folders and invalid intensity', () async {
    final store = SalonLookPresetStore(rootOverride: root, scope: 'salon-a');

    Future<void> saveWith({
      String name = 'Preset',
      String folder = 'Makeup',
      double intensity = 0.5,
    }) async {
      await store.save(
        name: name,
        folder: folder,
        engine: 'classic',
        makeupStyle: 'natural',
        generativeLook: 'natural',
        photoFinish: 'Natural Finish',
        intensity: intensity,
      );
    }

    await expectLater(saveWith(name: '  '), throwsArgumentError);
    await expectLater(saveWith(folder: 'Glasses'), throwsArgumentError);
    await expectLater(saveWith(intensity: 1.5), throwsArgumentError);
    expect(await store.list(), isEmpty);
  });

  test('deletes a preset by id', () async {
    final store = SalonLookPresetStore(rootOverride: root, scope: 'salon-a');
    final saved = await store.save(
      name: 'Everyday',
      folder: 'Skin',
      engine: 'classic',
      makeupStyle: 'skin_only',
      generativeLook: 'natural',
      photoFinish: 'Natural Finish',
      intensity: 0.6,
    );

    await store.delete(saved.id);
    expect(await store.list(), isEmpty);
  });
}
