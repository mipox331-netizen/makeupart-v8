import 'dart:convert';
import 'dart:io';

import 'package:path_provider/path_provider.dart';

class SalonLookPresetLimitException implements Exception {
  const SalonLookPresetLimitException(this.limit);

  final int limit;

  String get message =>
      'You can save up to $limit salon looks. Delete one before adding another.';

  @override
  String toString() => message;
}

/// A salon-scoped, device-local recipe for repeating a beauty edit.
///
/// Presets contain settings only; they never store client photos or personal data.
class SalonLookPreset {
  const SalonLookPreset({
    required this.id,
    required this.name,
    required this.folder,
    required this.engine,
    required this.makeupStyle,
    this.faceEdit = 'none',
    required this.generativeLook,
    required this.photoFinish,
    required this.intensity,
    this.brightness = 0.0,
    this.contrast = 1.0,
    this.saturation = 1.0,
    this.warmth = 0.0,
    this.sharpness = 0.0,
    required this.updatedAt,
  });

  final String id;
  final String name;
  final String folder;
  final String engine;
  final String makeupStyle;
  final String faceEdit;
  final String generativeLook;
  final String photoFinish;
  final double intensity;
  final double brightness;
  final double contrast;
  final double saturation;
  final double warmth;
  final double sharpness;
  final DateTime updatedAt;

  Map<String, Object> toJson() => {
        'id': id,
        'name': name,
        'folder': folder,
        'engine': engine,
        'makeup_style': makeupStyle,
        'face_edit': faceEdit,
        'generative_look': generativeLook,
        'photo_finish': photoFinish,
        'intensity': intensity,
        'brightness': brightness,
        'contrast': contrast,
        'saturation': saturation,
        'warmth': warmth,
        'sharpness': sharpness,
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
    final faceEditValue = json['face_edit'] ?? 'none';
    final faceEdit = faceEditValue is String ? faceEditValue : '';
    final generativeLook = requiredString('generative_look');
    final photoFinish = requiredString('photo_finish');
    final intensityValue = json['intensity'];
    final brightnessValue = json['brightness'] ?? 0.0;
    final contrastValue = json['contrast'] ?? 1.0;
    final saturationValue = json['saturation'] ?? 1.0;
    final warmthValue = json['warmth'] ?? 0.0;
    final sharpnessValue = json['sharpness'] ?? 0.0;
    final updatedAtValue = json['updated_at'];

    if (name.length > SalonLookPresetStore.maxNameLength ||
        !SalonLookPresetStore.supportedFolders.contains(folder) ||
        !const {'classic', 'generative'}.contains(engine) ||
        !SalonLookPresetStore.supportedFaceEdits.contains(faceEdit) ||
        intensityValue is! num ||
        !intensityValue.toDouble().isFinite ||
        intensityValue < 0 ||
        intensityValue > 1 ||
        brightnessValue is! num || !brightnessValue.toDouble().isFinite ||
        brightnessValue < -0.25 || brightnessValue > 0.25 ||
        contrastValue is! num || !contrastValue.toDouble().isFinite ||
        contrastValue < 0.5 || contrastValue > 1.5 ||
        saturationValue is! num || !saturationValue.toDouble().isFinite ||
        saturationValue < 0 || saturationValue > 2 ||
        warmthValue is! num || !warmthValue.toDouble().isFinite ||
        warmthValue < -0.25 || warmthValue > 0.25 ||
        sharpnessValue is! num || !sharpnessValue.toDouble().isFinite ||
        sharpnessValue < 0 || sharpnessValue > 1 ||
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
      faceEdit: faceEdit,
      generativeLook: generativeLook,
      photoFinish: photoFinish,
      intensity: intensityValue.toDouble(),
      brightness: brightnessValue.toDouble(),
      contrast: contrastValue.toDouble(),
      saturation: saturationValue.toDouble(),
      warmth: warmthValue.toDouble(),
      sharpness: sharpnessValue.toDouble(),
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
    'Sizes',
    'Hair Colors',
    'Smiles',
    'Features',
    'Beards',
    'Age',
    'Gender',
    'Glasses',
  };
  static const supportedFaceEdits = <String>{
    'none',
    'hair_black', 'hair_brown', 'hair_auburn', 'hair_blonde',
    'soft_smile', 'stubble', 'short_beard', 'full_beard', 'mustache',
    'glasses_round', 'glasses_square', 'glasses_aviator',
    'slim_face', 'v_shape', 'age_mature', 'youthful_finish',
    'masculine_presentation', 'feminine_presentation',
  };

  final Directory? rootOverride;
  final String scope;

  String get _safeScope {
    final normalizedScope = scope.trim();
    if (normalizedScope.isEmpty) {
      throw ArgumentError.value(scope, 'scope', 'must not be empty');
    }
    // Keep the existing on-device folder for UUIDs and other safe identifiers.
    if (RegExp(r'^[A-Za-z0-9_-]+$').hasMatch(normalizedScope)) {
      return normalizedScope;
    }
    // A leading tilde is outside the safe character set, preventing collisions.
    return '~${base64Url.encode(utf8.encode(normalizedScope)).replaceAll('=', '')}';
  }

  Future<File> _file({required bool createDirectory}) async {
    final root = rootOverride ?? await getApplicationDocumentsDirectory();
    final path =
        '${root.path}${Platform.pathSeparator}salon_look_presets${Platform.pathSeparator}$_safeScope';
    final directory = Directory(path);
    if (createDirectory && !await directory.exists()) {
      await directory.create(recursive: true);
    }
    return File('${directory.path}${Platform.pathSeparator}presets.json');
  }

  Future<void> _quarantineCorruptFile(File file) async {
    final suffix = DateTime.now().toUtc().microsecondsSinceEpoch;
    final backup = File('${file.path}.corrupt-$suffix');
    await file.rename(backup.path);
  }

  Future<List<SalonLookPreset>> list() async {
    final file = await _file(createDirectory: false);
    if (!await file.exists()) return const [];

    dynamic decoded;
    try {
      decoded = jsonDecode(await file.readAsString());
    } on FormatException {
      // Preserve damaged data for recovery, but do not let one corrupt file
      // permanently block saving new presets on this device.
      await _quarantineCorruptFile(file);
      return const [];
    }

    if (decoded is! Map<String, dynamic>) {
      await _quarantineCorruptFile(file);
      return const [];
    }
    if (decoded['schema_version'] != 1) {
      // A newer schema may contain data this app cannot safely rewrite.
      throw const FormatException('Saved salon looks file has an unsupported schema version');
    }
    if (decoded['presets'] is! List) {
      await _quarantineCorruptFile(file);
      return const [];
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
    String faceEdit = 'none',
    required String generativeLook,
    required String photoFinish,
    required double intensity,
    double brightness = 0.0,
    double contrast = 1.0,
    double saturation = 1.0,
    double warmth = 0.0,
    double sharpness = 0.0,
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
    if (!brightness.isFinite || brightness < -0.25 || brightness > 0.25) {
      throw ArgumentError('Brightness must be between -0.25 and 0.25.');
    }
    if (!contrast.isFinite || contrast < 0.5 || contrast > 1.5) {
      throw ArgumentError('Contrast must be between 0.5 and 1.5.');
    }
    if (!saturation.isFinite || saturation < 0 || saturation > 2) {
      throw ArgumentError('Saturation must be between 0 and 2.');
    }
    if (!warmth.isFinite || warmth < -0.25 || warmth > 0.25) {
      throw ArgumentError('Warmth must be between -0.25 and 0.25.');
    }
    if (!sharpness.isFinite || sharpness < 0 || sharpness > 1) {
      throw ArgumentError('Sharpness must be between 0 and 1.');
    }
    if (makeupStyle.trim().isEmpty ||
        !supportedFaceEdits.contains(faceEdit) ||
        generativeLook.trim().isEmpty ||
        photoFinish.trim().isEmpty) {
      throw ArgumentError('Preset settings cannot be empty.');
    }

    final existing = await list();
    final existingName = existing.where(
      (preset) => preset.name.toLowerCase() == cleanName.toLowerCase(),
    );
    final previous = existingName.isEmpty ? null : existingName.first;
    if (previous == null && existing.length >= maxPresets) {
      // Never silently evict an existing salon recipe when the user saves
      // a new one. Existing presets can still be updated at the limit.
      throw const SalonLookPresetLimitException(maxPresets);
    }
    final now = DateTime.now().toUtc();
    final preset = SalonLookPreset(
      id: previous?.id ?? now.microsecondsSinceEpoch.toString(),
      name: cleanName,
      folder: folder,
      engine: engine,
      makeupStyle: makeupStyle,
      faceEdit: faceEdit,
      generativeLook: generativeLook,
      photoFinish: photoFinish,
      intensity: intensity,
      brightness: brightness,
      contrast: contrast,
      saturation: saturation,
      warmth: warmth,
      sharpness: sharpness,
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
