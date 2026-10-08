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

  Future<Directory?> _phoneStorageDirectory() async {
    final override = phoneRootOverride;
    if (override != null) {
      final directory = Directory(
        '${override.path}${Platform.pathSeparator}MakeupArtV8${Platform.pathSeparator}$_safeScope',
      );
      await directory.create(recursive: true);
      return directory;
    }

    if (!Platform.isAndroid) return null;
    final directories = await getExternalStorageDirectories(
      type: StorageDirectory.pictures,
    );
    if (directories == null || directories.isEmpty) return null;

    final directory = Directory(
      '${directories.first.path}${Platform.pathSeparator}MakeupArtV8',
    );
    await directory.create(recursive: true);
    return directory;
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
      try {
        if (phoneDirectory == null) {
          await file.delete();
          continue;
        }

        final target = File(
          '${phoneDirectory.path}${Platform.pathSeparator}${file.uri.pathSegments.last}',
        );
        await file.copy(target.path);
        await file.delete();
      } on FileSystemException {
        // If phone storage is unavailable, remove the overflow copy rather
        // than letting private app storage grow without bounds.
        try {
          await file.delete();
        } on FileSystemException {
          // Another cleanup operation may have removed it already.
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