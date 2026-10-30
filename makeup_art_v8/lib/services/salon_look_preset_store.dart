import 'dart:convert';
import 'dart:io';

import 'package:path_provider/path_provider.dart';

/// A salon-scoped, device-local recipe for repeating a beauty edit.
/// Presets contain settings only; they never store client photos or personal data.
class SalonLookPreset {
  const SalonLookPreset({
    required this.id,
    required this.name,
    required this.folder,
    required this.engine,
    required this.makeupStyle,
    required this.generativeLook,
    required this.photoFinish,
    required this.intensity,
    required this.updatedAt,
  });

  final String id;
  final String name;
  final String folder;
  final String engine;
  final String makeupStyle;
  final String generativeLook;
  final String photoFinish;
  final double intensity;
  final DateTime updatedAt;

  Map<String, Object> toJson() => {
        'id': id,
        'name': name,
        'folder': folder,
        'engine': engine,
        'makeup_style': makeupStyle,
        'generative_look': generativeLook,
        'photo_finish': photoFinish,
        'intensity': intensity,
        'updated_at': updatedAt.toUtc().toIso8601String(),
      };

  factory SalonLookPreset.fromJson(Map<String, dynamic> json) {
    String requiredString(String key) {
      final value = json[key];
      if (value is! String || value.trim().isEmpty) {
        throw FormatException('Invalid salon look preset field: $key');
      }
      return value.trim();
    }

    final id = requiredString('id');
    final name = requiredString('name');
    final folder = requiredString('folder');
    final engine = requiredString('engine');
    final makeupStyle = requiredString('makeup_style');
    final generativeLook = requiredString('generative_look');
    final photoFinish = requiredString('photo_finish');
    final intensityValue = json['intensity'];
    final updatedAtValue = json['updated_at'];

    if (name.length > SalonLookPresetStore.maxNameLength ||
        !SalonLookPresetStore.supportedFolders.contains(folder) ||
        !const {'classic', 'generative'}.contains(engine) ||
        intensityValue is! num ||
        !intensityValue.toDouble().isFinite ||
        intensityValue < 0 ||
        intensityValue > 1 ||
        updatedAtValue is! String) {
      throw const FormatException('Invalid salon look preset data');
    }

    final updatedAt = DateTime.tryParse(updatedAtValue);
    if (updatedAt == null) {
      throw const FormatException('Invalid salon look preset timestamp');
    }

    return SalonLookPreset(
      id: id,
      name: name,
      folder: folder,
      engine: engine,
      makeupStyle: makeupStyle,
      generativeLook: generativeLook,
      photoFinish: photoFinish,
      intensity: intensityValue.toDouble(),
      updatedAt: updatedAt.toUtc(),
    );
  }
}

class SalonLookPresetStore {
  const SalonLookPresetStore({
    this.rootOverride,
    required this.scope,
  });

  static const maxPresets = 24;
  static const maxNameLength = 32;
  static const supportedFolders = <String>{
    'Impression',
    'Skin',
    'Makeup',
    'Hairstyles',
  };

  final Directory? rootOverride;
  final String scope;

  // Encode the complete salon identifier instead of replacing characters.
  // Character replacement can make two different salon IDs share one folder.
  String get _safeScope {
    final normalizedScope = scope.trim();
    if (normalizedScope.isEmpty) {
      throw ArgumentError.value(scope, 'scope', 'must not be empty');
    }
    return base64Url.encode(utf8.encode(normalizedScope)).replaceAll('=', '');
  }

  Future<File> _file({required bool createDirectory}) async {
    final root = rootOverride ?? await getApplicationDocumentsDirectory();
    final directory = Directory(
      '${root.path}${Platform.pathSeparator}salon_look_presets${Platform.pathSeparator}$_safeScope',
    );
    if (createDirectory && !await directory.exists()) {
      await directory.create(recursive: true);
    }
    return File(
      '${directory.path}${Platform.pathSeparator}presets.json',
    );
  }

  Future<List<SalonLookPreset>> list() async {
    final file = await _file(createDirectory: false);
    if (!await file.exists()) return const [];

    final decoded = jsonDecode(await file.readAsString());
    if (decoded is! Map<String, dynamic> ||
        decoded['schema_version'] != 1 ||
        decoded['presets'] is! List) {
      throw const FormatException('Saved salon looks file has an unsupported format');
    }

    final presets = <SalonLookPreset>[];
    for (final value in decoded['presets'] as List<dynamic>) {
      if (value is! Map<String, dynamic>) continue;
      try {
        presets.add(SalonLookPreset.fromJson(value));
      } on FormatException {
        // Ignore a damaged individual record without discarding other saved looks.
      }
    }
    presets.sort((a, b) => b.updatedAt.compareTo(a.updatedAt));
    return presets;
  }

  Future<SalonLookPreset> save({
    required String name,
    required String folder,
    required String engine,
    required String makeupStyle,
    required String generativeLook,
    required String photoFinish,
    required double intensity,
  }) async {
    final cleanName = name.trim();
    if (cleanName.isEmpty || cleanName.length > maxNameLength) {
      throw ArgumentError('Name must contain 1–$maxNameLength characters.');
    }
    if (!supportedFolders.contains(folder)) {
      throw ArgumentError('This filter folder cannot be saved as a preset.');
    }
    if (!const {'classic', 'generative'}.contains(engine)) {
      throw ArgumentError('Unknown beauty engine.');
    }
    if (!intensity.isFinite || intensity < 0 || intensity > 1) {
      throw ArgumentError('Intensity must be between 0 and 1.');
    }
    if (makeupStyle.trim().isEmpty ||
        generativeLook.trim().isEmpty ||
        photoFinish.trim().isEmpty) {
      throw ArgumentError('Preset settings cannot be empty.');
    }

    final existing = await list();
    final existingName = existing.where(
      (preset) => preset.name.toLowerCase() == cleanName.toLowerCase(),
    );
    final previous = existingName.isEmpty ? null : existingName.first;
    final now = DateTime.now().toUtc();
    final preset = SalonLookPreset(
      id: previous?.id ?? now.microsecondsSinceEpoch.toString(),
      name: cleanName,
      folder: folder,
      engine: engine,
      makeupStyle: makeupStyle,
      generativeLook: generativeLook,
      photoFinish: photoFinish,
      intensity: intensity,
      updatedAt: now,
    );
    final next = <SalonLookPreset>[
      preset,
      ...existing.where((item) => item.id != preset.id),
    ]..sort((a, b) => b.updatedAt.compareTo(a.updatedAt));

    await _write(next.take(maxPresets).toList());
    return preset;
  }

  Future<void> delete(String id) async {
    final existing = await list();
    final next = existing.where((preset) => preset.id != id).toList();
    if (next.length == existing.length) return;
    await _write(next);
  }

  Future<void> _write(List<SalonLookPreset> presets) async {
    final file = await _file(createDirectory: true);
    final temporary = File('${file.path}.tmp');
    if (await temporary.exists()) await temporary.delete();
    await temporary.writeAsString(
      jsonEncode({
        'schema_version': 1,
        'presets': presets.map((preset) => preset.toJson()).toList(),
      }),
      flush: true,
    );
    // Rename within the same directory so readers never observe a half-written JSON file.
    await temporary.rename(file.path);
  }
}
