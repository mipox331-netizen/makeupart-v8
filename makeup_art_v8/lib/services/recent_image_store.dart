import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:path_provider/path_provider.dart';

class RecentImageStore {
  static const maxImages = 10;
  static const _directoryName = 'recent_ai_results';

  final Directory? rootOverride;
  final Directory? phoneRootOverride;
  final String scope;

  const RecentImageStore({
    this.rootOverride,
    this.phoneRootOverride,
    this.scope = 'default',
  });

  String get _safeScope {
    final normalizedScope = scope.trim();
    if (normalizedScope.isEmpty) {
      throw ArgumentError.value(scope, 'scope', 'must not be empty');
    }
    // Preserve historical paths for UUIDs and the default scope.
    if (RegExp(r'^[A-Za-z0-9_-]+$').hasMatch(normalizedScope)) {
      return normalizedScope;
    }
    // Tilde is excluded from the safe character set, so encoded values cannot
    // collide with a literal safe scope or with another normalized scope.
    return '~${base64Url.encode(utf8.encode(normalizedScope)).replaceAll('=', '')}';
  }

  String _safeJobToken(String value) {
    if (RegExp(r'^[A-Za-z0-9_-]+$').hasMatch(value)) {
      return value;
    }
    return '~${base64Url.encode(utf8.encode(value)).replaceAll('=', '')}';
  }

  Future<Directory> _directory() async {
    final root = rootOverride ?? await getApplicationDocumentsDirectory();
    final path =
        '${root.path}${Platform.pathSeparator}$_directoryName${Platform.pathSeparator}$_safeScope';
    final directory = Directory(path);
    if (!await directory.exists()) {
      await directory.create(recursive: true);
    }
    return directory;
  }

  Future<Directory> _scopedPhoneStorageDirectory(String parentPath) async {
    final path = parentPath +
        Platform.pathSeparator +
        'MakeupArtV8' +
        Platform.pathSeparator +
        _safeScope;
    final directory = Directory(path);
    await directory.create(recursive: true);
    return directory;
  }

  Future<Directory?> _phoneStorageDirectory() async {
    final override = phoneRootOverride;
    if (override != null) {
      return _scopedPhoneStorageDirectory(override.path);
    }

    if (!Platform.isAndroid) return null;
    final directories = await getExternalStorageDirectories(
      type: StorageDirectory.pictures,
    );
    if (directories == null || directories.isEmpty) return null;

    // Isolate archived client photos by salon on the device as well as in app storage.
    return _scopedPhoneStorageDirectory(directories.first.path);
  }

  Future<List<File>> list() async {
    final directory = await _directory();
    final files = await directory
        .list()
        .where((entity) => entity is File)
        .cast<File>()
        .where((file) => file.path.toLowerCase().endsWith('.png'))
        .toList();

    files.sort((a, b) {
      final aModified = a.statSync().modified;
      final bModified = b.statSync().modified;
      return bModified.compareTo(aModified);
    });

    return files.take(maxImages).toList();
  }

  Future<File> save(Uint8List bytes, {String? jobId}) async {
    if (bytes.isEmpty) {
      throw ArgumentError.value(bytes, 'bytes', 'Image bytes cannot be empty.');
    }

    final directory = await _directory();
    final rawJobId = jobId ?? 'result';
    final safeJobId = rawJobId.isEmpty ? 'result' : _safeJobToken(rawJobId);

    // Processing saves an image to history, and a later gallery export can
    // save the selected photo finish again. Reuse the same job's history entry
    // instead of creating duplicate tiles and archiving unrelated older photos.
    if (jobId != null && jobId.isNotEmpty) {
      final matches = await directory
          .list()
          .where((entity) => entity is File)
          .cast<File>()
          .where(
            (file) => file.uri.pathSegments.last.endsWith('_${safeJobId}.png'),
          )
          .toList();
      matches.sort(
        (a, b) => b.statSync().modified.compareTo(a.statSync().modified),
      );
      if (matches.isNotEmpty) {
        final existing = matches.first;
        await existing.writeAsBytes(bytes, flush: true);
        for (final duplicate in matches.skip(1)) {
          try {
            await duplicate.delete();
          } on FileSystemException {
            // Keep a duplicate if cleanup fails; never risk losing the updated result.
          }
        }
        await trim();
        return existing;
      }
    }

    final fileJobId = safeJobId.isEmpty ? 'result' : safeJobId;
    final filename =
        'ai_${DateTime.now().microsecondsSinceEpoch}_$fileJobId.png';
    final file = File('${directory.path}${Platform.pathSeparator}$filename');

    await file.writeAsBytes(bytes, flush: true);
    await trim();
    return file;
  }

  Future<void> trim() async {
    final directory = await _directory();
    final files = await directory
        .list()
        .where((entity) => entity is File)
        .cast<File>()
        .where((file) => file.path.toLowerCase().endsWith('.png'))
        .toList();

    files.sort((a, b) {
      final aModified = a.statSync().modified;
      final bModified = b.statSync().modified;
      return bModified.compareTo(aModified);
    });

    final overflow = files.skip(maxImages);
    final phoneDirectory = await _phoneStorageDirectory();

    for (final file in overflow) {
      File? target;
      try {
        if (phoneDirectory == null) {
          // Preserve older photos when external phone storage is unavailable.
          // They may temporarily remain in app storage until archiving succeeds.
          continue;
        }

        target = File(
          phoneDirectory.path +
              Platform.pathSeparator +
              file.uri.pathSegments.last,
        );
        await file.copy(target.path);
        await file.delete();
      } on FileSystemException {
        // Never delete the only remaining copy if archiving fails.
        if (target != null) {
          try {
            await target.delete();
          } on FileSystemException {
            // The partial archive may already have been removed.
          }
        }
      }
    }
  }

  Future<void> clear() async {
    final directory = await _directory();
    if (await directory.exists()) {
      await directory.delete(recursive: true);
    }
  }
}
