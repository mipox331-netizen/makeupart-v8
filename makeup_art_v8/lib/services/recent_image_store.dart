import 'dart:io';
import 'dart:typed_data';

import 'package:path_provider/path_provider.dart';

class RecentImageStore {
  static const maxImages = 10;
  static const _directoryName = 'recent_ai_results';

  final Directory? rootOverride;
  final String scope;

  const RecentImageStore({
    this.rootOverride,
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

    for (final file in files.skip(maxImages)) {
      try {
        await file.delete();
      } on FileSystemException {
        // Another cleanup operation may have removed it already.
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