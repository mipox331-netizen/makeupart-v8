import 'dart:io';
import 'dart:typed_data';

import 'package:path_provider/path_provider.dart';

/// Private on-device favorites, scoped by salon and never uploaded separately.
class FavoriteImageStore {
  static const _directoryName = 'favorite_ai_results';

  final Directory? rootOverride;
  final String scope;

  const FavoriteImageStore({this.rootOverride, required this.scope});

  String get _safeScope =>
      scope.replaceAll(RegExp(r'[^A-Za-z0-9_-]'), '_');

  String _safeJobId(String jobId) {
    final value = jobId.replaceAll(RegExp(r'[^A-Za-z0-9_-]'), '');
    if (value.isEmpty) {
      throw ArgumentError.value(jobId, 'jobId', 'A valid result id is required.');
    }
    return value;
  }

  Future<Directory> _directory() async {
    final root = rootOverride ?? await getApplicationDocumentsDirectory();
    final directory = Directory(
      '${root.path}${Platform.pathSeparator}$_directoryName${Platform.pathSeparator}$_safeScope',
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
    files.sort((a, b) => b.statSync().modified.compareTo(a.statSync().modified));
    return files;
  }

  Future<bool> contains(String jobId) async {
    final directory = await _directory();
    final file = File(
      '${directory.path}${Platform.pathSeparator}favorite_${_safeJobId(jobId)}.png',
    );
    return file.exists();
  }

  Future<File> save(Uint8List bytes, {required String jobId}) async {
    if (bytes.isEmpty) {
      throw ArgumentError.value(bytes, 'bytes', 'Image bytes cannot be empty.');
    }
    final directory = await _directory();
    final name = 'favorite_${_safeJobId(jobId)}.png';
    final target = File('${directory.path}${Platform.pathSeparator}$name');
    final temporary = File(
      '${directory.path}${Platform.pathSeparator}.${name}_${DateTime.now().microsecondsSinceEpoch}.tmp',
    );
    try {
      await temporary.writeAsBytes(bytes, flush: true);
      if (await target.exists()) await target.delete();
      return await temporary.rename(target.path);
    } on FileSystemException {
      await temporary.delete().catchError((_) => temporary);
      rethrow;
    }
  }

  Future<void> remove(String jobId) async {
    final directory = await _directory();
    final file = File(
      '${directory.path}${Platform.pathSeparator}favorite_${_safeJobId(jobId)}.png',
    );
    if (await file.exists()) await file.delete();
  }

  Future<void> clear() async {
    final directory = await _directory();
    if (await directory.exists()) {
      await directory.delete(recursive: true);
    }
  }
}
