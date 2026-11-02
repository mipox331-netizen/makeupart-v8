import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:path_provider/path_provider.dart';

import 'gallery_exporter.dart';

class PhonePhotoBackupResult {
  final int total;
  final int saved;
  final int failed;

  const PhonePhotoBackupResult({
    required this.total,
    required this.saved,
    required this.failed,
  });

  bool get isComplete => failed == 0;
}

class RecentImageStore {
  static const maxImages = 10;
  static const _directoryName = 'recent_ai_results';

  final Directory? rootOverride;
  final Future<void> Function(Uint8List bytes, String fileName)?
      galleryArchiveWriter;
  final String scope;

  const RecentImageStore({
    this.rootOverride,
    this.galleryArchiveWriter,
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

  String _galleryBackupFileName(File file) {
    // Dots are excluded from plain salon IDs, so this marker keeps encoded
    // salon scopes distinct after the name is normalized for MediaStore.
    final safeScope = _safeScope;
    final scopeToken = safeScope.startsWith('~')
        ? '.${safeScope.substring(1)}'
        : safeScope;
    return 'backup_${scopeToken}_${file.uri.pathSegments.last}';
  }

  Future<void> _writeGalleryBackup(File file) async {
    final bytes = await file.readAsBytes();
    final writer = galleryArchiveWriter;
    if (writer != null) {
      await writer(bytes, _galleryBackupFileName(file));
      return;
    }
    if (Platform.isAndroid) {
      await GalleryExporter.savePng(
        bytes: bytes,
        fileName: _galleryBackupFileName(file),
      );
      return;
    }
    throw UnsupportedError('Phone Gallery backup is currently supported on Android.');
  }

  Future<List<File>> listAll() async {
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
    return files;
  }

  Future<List<File>> list() async {
    final files = await listAll();
    return files.take(maxImages).toList();
  }

  /// Copies every locally retained result to the phone's shared Pictures
  /// collection. Existing deterministic names are overwritten by MediaStore,
  /// so pressing Backup Now repeatedly does not create duplicate backups.
  Future<PhonePhotoBackupResult> backupAllToGallery() async {
    final files = await listAll();
    var saved = 0;
    var failed = 0;

    for (final file in files) {
      try {
        await _writeGalleryBackup(file);
        saved++;
      } catch (_) {
        failed++;
      }
    }
    return PhonePhotoBackupResult(
      total: files.length,
      saved: saved,
      failed: failed,
    );
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
            (file) => file.uri.pathSegments.last.endsWith('_$safeJobId.png'),
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

    // Back up each processed result immediately. If Gallery is unavailable
    // (for example, storage is full), keep the private source untouched.
    try {
      await _writeGalleryBackup(file);
    } catch (_) {
      // The private copy is the fallback until a later backup succeeds.
    }

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

    for (final file in overflow) {
      try {
        // Keep at most ten private recent results. The older source is removed
        // only after its stable Gallery backup is confirmed.
        await _writeGalleryBackup(file);
        await file.delete();
      } catch (_) {
        // Gallery permission, MediaStore or filesystem failures must never
        // delete the only remaining copy of a customer's photo.
        continue;
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
