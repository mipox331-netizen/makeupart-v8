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

  test('persists manual photo adjustments and reads older presets with defaults', () async {
    final store = SalonLookPresetStore(rootOverride: root, scope: 'salon-adjustments');
    final saved = await store.save(
      name: 'Studio Finish',
      folder: 'Impression',
      engine: 'classic',
      makeupStyle: 'skin_only',
      generativeLook: 'natural',
      photoFinish: 'Golden Hour',
      intensity: 0.72,
      brightness: 0.10,
      contrast: 1.18,
      saturation: 1.25,
      warmth: 0.16,
      sharpness: 0.45,
    );

    final loaded = (await store.list()).single;
    expect(loaded.id, saved.id);
    expect(loaded.brightness, closeTo(0.10, 0.0001));
    expect(loaded.contrast, closeTo(1.18, 0.0001));
    expect(loaded.saturation, closeTo(1.25, 0.0001));
    expect(loaded.warmth, closeTo(0.16, 0.0001));
    expect(loaded.sharpness, closeTo(0.45, 0.0001));

    final legacy = SalonLookPreset.fromJson({
      'id': 'legacy',
      'name': 'Old recipe',
      'folder': 'Skin',
      'engine': 'classic',
      'makeup_style': 'skin_only',
      'generative_look': 'natural',
      'photo_finish': 'Natural Finish',
      'intensity': 0.5,
      'updated_at': DateTime.utc(2026, 1, 1).toIso8601String(),
    });
    expect(legacy.faceEdit, 'none');
    expect(legacy.brightness, 0.0);
    expect(legacy.contrast, 1.0);
    expect(legacy.saturation, 1.0);
    expect(legacy.warmth, 0.0);
    expect(legacy.sharpness, 0.0);
  });

  test('persists local face edits and accepts every implemented folder', () async {
    final store = SalonLookPresetStore(rootOverride: root, scope: 'salon-face-edits');
    final saved = await store.save(
      name: 'Round Glasses',
      folder: 'Glasses',
      engine: 'classic',
      makeupStyle: 'natural',
      faceEdit: 'glasses_round',
      generativeLook: 'natural',
      photoFinish: 'Natural Finish',
      intensity: 0.72,
    );

    final loaded = (await store.list()).single;
    expect(loaded.id, saved.id);
    expect(loaded.folder, 'Glasses');
    expect(loaded.faceEdit, 'glasses_round');
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
    await expectLater(saveWith(folder: 'Not a real folder'), throwsArgumentError);
    await expectLater(saveWith(intensity: 1.5), throwsArgumentError);
    expect(await store.list(), isEmpty);
  });

  test('quarantines malformed JSON and allows new presets to be saved', () async {
    final store = SalonLookPresetStore(rootOverride: root, scope: 'salon-a');
    final directory = Directory(
      '${root.path}${Platform.pathSeparator}salon_look_presets'
      '${Platform.pathSeparator}salon-a',
    );
    await directory.create(recursive: true);
    final file = File('${directory.path}${Platform.pathSeparator}presets.json');
    await file.writeAsString('{ malformed json');

    expect(await store.list(), isEmpty);
    expect(await file.exists(), isFalse);

    final quarantined = await directory
        .list()
        .where((entity) => entity is File)
        .cast<File>()
        .toList();
    expect(quarantined, hasLength(1));
    expect(quarantined.single.path, contains('.corrupt-'));

    final saved = await store.save(
      name: 'Fresh Start',
      folder: 'Skin',
      engine: 'classic',
      makeupStyle: 'skin_only',
      generativeLook: 'natural',
      photoFinish: 'Natural Finish',
      intensity: 0.5,
    );
    expect((await store.list()).single.id, saved.id);
  });

  test('does not silently evict saved looks when the 24-preset limit is reached', () async {
    final store = SalonLookPresetStore(rootOverride: root, scope: 'salon-a');

    for (var index = 0; index < SalonLookPresetStore.maxPresets; index++) {
      await store.save(
        name: 'Look $index',
        folder: 'Makeup',
        engine: 'classic',
        makeupStyle: 'natural',
        generativeLook: 'natural',
        photoFinish: 'Natural Finish',
        intensity: 0.5,
      );
    }

    await expectLater(
      store.save(
        name: 'Look 24',
        folder: 'Makeup',
        engine: 'classic',
        makeupStyle: 'natural',
        generativeLook: 'natural',
        photoFinish: 'Natural Finish',
        intensity: 0.5,
      ),
      throwsA(isA<SalonLookPresetLimitException>()),
    );

    final saved = await store.list();
    expect(saved, hasLength(SalonLookPresetStore.maxPresets));
    expect(saved.map((preset) => preset.name), contains('Look 0'));
    expect(saved.map((preset) => preset.name), contains('Look 23'));

    // Updating an existing preset remains allowed at the limit.
    await store.save(
      name: 'Look 0',
      folder: 'Makeup',
      engine: 'classic',
      makeupStyle: 'soft_glam',
      generativeLook: 'natural',
      photoFinish: 'Natural Finish',
      intensity: 0.7,
    );
    expect(await store.list(), hasLength(SalonLookPresetStore.maxPresets));
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
