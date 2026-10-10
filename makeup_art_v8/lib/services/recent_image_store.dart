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

  Future<Directory> _directory() async {
    final root = rootOverride ?? await getApplicationDocumentsDirectory();
    final safeScope = scope.replaceAll(RegExp(r'[^A-Za-z0-9_-]'), '_');
    final directory = Directory(
      '${root.path}${Platform.pathSeparator}$_directoryName${Platform.pathSeparator}$safeScope',
    );
    if (!await directory.exists()) {
      await directory.create(recursive: true);
    }
    return directory;
  }

  Future<Directory> _scopedPhoneStorageDirectory(String parentPath) async {
    final directory = Directory(
      '$parentPath${Platform.pathSeparator}MakeupArtV8${Platform.pathSeparator}$_safeScope',
    );
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

  String get _safeScope =>
      scope.replaceAll(RegExp(r'[^A-Za-z0-9_-]'), '_');

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
    final directory = await _directory();
    final safeJobId = (jobId ?? 'result')
        .replaceAll(RegExp(r'[^A-Za-z0-9_-]'), '');
    final filename =
        'ai_${DateTime.now().microsecondsSinceEpoch}_$safeJobId.png';
    final file = File(
      '${directory.path}${Platform.pathSeparator}$filename',
    );

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
          '${phoneDirectory.path}${Platform.pathSeparator}${file.uri.pathSegments.last}',
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